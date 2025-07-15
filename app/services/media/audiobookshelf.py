from __future__ import annotations

import logging
import re
from typing import Any

from app.extensions import db
from app.models import Library, User

from .client_base import RestApiMixin, register_media_client

"""Minimal Audiobookshelf media‐server client.

This aims to provide just enough functionality so that Wizarr can:
  * validate connection credentials (URL & API token)
  * scan libraries so that they can be enabled / disabled in the UI
  * list users (read-only) so that the admin section doesn't explode

User management (create / update / delete) isn't currently supported by
this client – the Audiobookshelf HTTP API requires admin privileges and
has a few additional concepts (permissions, library access, …) that we
haven't mapped yet.  The corresponding methods therefore raise
``NotImplementedError`` so that callers know this path isn't available
for Audiobookshelf yet.
"""


@register_media_client("audiobookshelf")
class AudiobookshelfClient(RestApiMixin):
    """Very small wrapper around the Audiobookshelf REST API."""

    #: API prefix that all modern ABS endpoints share
    API_PREFIX = "/api"

    EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")

    def __init__(self, *args, **kwargs):
        # Provide defaults so legacy code keeps working if the caller didn't
        # specify explicit keys / MediaServer.
        if "url_key" not in kwargs:
            kwargs["url_key"] = "server_url"
        if "token_key" not in kwargs:
            kwargs["token_key"] = "api_key"

        super().__init__(*args, **kwargs)

        # Strip trailing slash to keep URL join sane.
        if self.url and self.url.endswith("/"):
            self.url = self.url.rstrip("/")

    # ------------------------------------------------------------------
    # Public API expected by Wizarr
    # ------------------------------------------------------------------

    # --- libraries -----------------------------------------------------

    def libraries(self) -> dict[str, str]:
        """Return mapping of ``library_id`` → ``display_name``.

        Audiobookshelf exposes ``GET /api/libraries`` which returns
        ``{"libraries": [ … ]}``.
        """
        try:
            data = self.get(f"{self.API_PREFIX}/libraries").json()
            # May have drilldown or direct list depending on ABS version
            libs = data.get("libraries", data)
            return {item["id"]: item["name"] for item in libs}
        except Exception as exc:
            logging.warning("ABS: failed to fetch libraries – %s", exc)
            return {}

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        """Scan available libraries on this Audiobookshelf server.

        Args:
            url: Optional server URL override
            token: Optional API token override

        Returns:
            dict: Library name -> library ID mapping
        """
        import requests

        if url and token:
            # Use override credentials for scanning
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{url.rstrip('/')}/api/libraries", headers=headers, timeout=10
            )
            response.raise_for_status()
            data = response.json()
            libs = data.get("libraries", data)
        else:
            # Use saved credentials
            data = self.get(f"{self.API_PREFIX}/libraries").json()
            libs = data.get("libraries", data)

        return {item["name"]: item["id"] for item in libs}

    # --- users ---------------------------------------------------------

    def list_users(self) -> list[User]:
        """Read users from Audiobookshelf and reflect them locally."""
        server_id = getattr(self, "server_id", None)
        if server_id is None:
            return []

        try:
            data = self.get(f"{self.API_PREFIX}/users").json()
            raw_users: list[dict[str, Any]] = data.get("users", data)
        except Exception as exc:
            logging.warning("ABS: failed to list users – %s", exc)
            return []

        raw_by_id = {u["id"]: u for u in raw_users}

        try:
            # Add new users or update existing ones
            for uid, remote in raw_by_id.items():
                db_row = User.query.filter_by(token=uid, server_id=server_id).first()
                if not db_row:
                    db_row = User(
                        token=uid,
                        username=remote.get("username", "abs-user"),
                        email=remote.get("email", ""),
                        code="empty",
                        server_id=server_id,
                    )
                    db.session.add(db_row)
                else:
                    db_row.username = remote.get("username", db_row.username)
                    db_row.email = remote.get("email", db_row.email)

            # Remove users that no longer exist upstream
            to_check = User.query.filter(User.server_id == server_id).all()
            for local in to_check:
                if local.token not in raw_by_id:
                    db.session.delete(local)

            db.session.commit()

        except Exception as exc:
            logging.error("ABS: failed to sync users – %s", exc)
            db.session.rollback()
            return []

        return User.query.filter(User.server_id == server_id).all()

    # --- user management ------------------------------------------------

    def create_user(
        self,
        username: str,
        password: str,
        email: str,
        *,
        is_admin: bool = False,
        allow_downloads: bool = True,
    ) -> str:
        """Create a user and return the Audiobookshelf user‐ID.

        The ABS API expects at least ``username``.  A password can be an
        empty string (guest), but Wizarr always passes one.
        """
        permissions = {
            "download": allow_downloads,
            "update": False,
            "delete": False,
            "upload": False,
            "accessAllLibraries": False,
            "accessAllTags": True,
            "accessExplicitContent": True,
        }

        payload = {
            "username": username,
            "password": password,
            "isActive": True,
            "email": email,
            "type": "admin" if is_admin else ("user" if allow_downloads else "guest"),
            "permissions": permissions,
        }
        resp = self.post(f"{self.API_PREFIX}/users", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("id") or data.get("user", {}).get("id")

    def update_user(self, user_id: str, payload: dict[str, Any]):
        """PATCH arbitrary fields on a user object."""
        resp = self.patch(f"{self.API_PREFIX}/users/{user_id}", json=payload)
        resp.raise_for_status()
        return resp.json()

    def delete_user(self, user_id: str):
        """Delete a user permanently from Audiobookshelf."""
        resp = self.delete(f"{self.API_PREFIX}/users/{user_id}")
        # 204 No Content or 200
        if resp.status_code not in (200, 204):
            resp.raise_for_status()

    def get_user(self, user_id: str):
        """Return a full user object from Audiobookshelf."""
        return self.get(f"{self.API_PREFIX}/users/{user_id}").json()

    # ------------------------------------------------------------------
    # Public sign-up (invite links)
    # ------------------------------------------------------------------

    def _password_for_db(self, password: str) -> str:
        """Return the password value to store in the local DB (plain)."""
        return password

    @staticmethod
    def _mark_invite_used(inv, user):
        inv.used_by = user
        from app.services.invites import mark_server_used

        mark_server_used(inv, user.server_id)

    def _set_specific_libraries(
        self, user_id: str, library_ids: list[str], allow_downloads: bool = True
    ):
        """Restrict the given *user* to the supplied library IDs.

        If *library_ids* is empty, the account will be granted access to all
        libraries (ABS default behaviour).
        """
        # Fetch current user object so that we do not accidentally wipe other fields
        try:
            current = self.get_user(user_id)
        except Exception as exc:
            logging.warning("ABS: failed to read user %s – %s", user_id, exc)
            return

        perms = current.get("permissions", {}) or {}
        perms["accessAllLibraries"] = not library_ids
        perms["download"] = allow_downloads

        patch = {
            "permissions": perms,
            # Root-level list of library IDs that the user may access
            "librariesAccessible": library_ids if library_ids else [],
            # Update user type based on download permission
            "type": "user" if allow_downloads else "guest",
        }

        try:
            self.update_user(user_id, patch)
        except Exception:
            logging.exception("ABS: failed to update permissions for %s", user_id)

    def join(self, username: str, password: str, confirm: str, email: str, code: str):
        """Public invite flow for Audiobookshelf users."""
        from sqlalchemy import or_

        from app.models import Invitation, User
        from app.services.invites import is_invite_valid

        if not self.EMAIL_RE.fullmatch(email):
            return False, "Invalid e-mail address."
        if not 8 <= len(password) <= 20:
            return False, "Password must be 8–20 characters."
        if password != confirm:
            return False, "Passwords do not match."

        ok, msg = is_invite_valid(code)
        if not ok:
            return False, msg

        server_id = getattr(self, "server_id", None)
        if server_id is None:
            return False, "Server configuration error"

        existing = User.query.filter(
            or_(User.username == username, User.email == email),
            User.server_id == server_id,
        ).first()
        if existing:
            return False, "User or e-mail already exists."

        try:
            inv = Invitation.query.filter_by(code=code).first()

            # Get download permission from invitation (default to True if not set)
            allow_downloads = getattr(inv, "allow_downloads", True)
            if allow_downloads is None:
                allow_downloads = True

            user_id = self.create_user(
                username, password, email=email, allow_downloads=allow_downloads
            )
            if not user_id:
                return False, "Failed to create user on server"

            # Set library access
            if inv and inv.libraries:
                lib_ids = [
                    lib.external_id
                    for lib in inv.libraries
                    if lib.server_id == server_id
                ]
            else:
                lib_ids = [
                    lib.external_id
                    for lib in Library.query.filter_by(
                        enabled=True, server_id=server_id
                    ).all()
                ]
            self._set_specific_libraries(user_id, lib_ids, allow_downloads)

            # Calculate expiry
            expires = None
            if inv and inv.duration:
                try:
                    import datetime as _dt

                    expires = _dt.datetime.utcnow() + _dt.timedelta(
                        days=int(inv.duration)
                    )
                except Exception:
                    pass

            # Store locally
            local = User(
                token=user_id,
                username=username,
                email=email,
                code=code,
                expires=expires,
                server_id=server_id,
            )
            db.session.add(local)
            db.session.commit()

            self._mark_invite_used(inv, local)
            return True, ""

        except Exception as exc:
            logging.error("ABS join failed: %s", exc)
            db.session.rollback()
            return False, "Failed to create user"

    def now_playing(self) -> list[dict]:
        """Return active sessions (updated within the last minute).

        AudioBookShelf lists sessions in chronological order (oldest first).
        We first fetch pagination metadata, then request the last page with
        10 items per page to retrieve the most recent sessions and filter
        them by activity timestamp.
        """
        import time

        endpoint = f"{self.API_PREFIX}/sessions"

        # --- Step 1: read pagination metadata with a minimal request ---------
        query: list[str] = ["itemsPerPage=1", "page=0"]
        if self.token:
            query.insert(0, f"token={self.token}")
        first_page_url = f"{endpoint}?{'&'.join(query)}"
        meta = self.get(first_page_url).json()

        total_sessions: int = meta.get("total", 0)
        if not total_sessions:
            return []  # Nothing playing at all

        # --- Step 2: fetch the last page with a fixed page size -------------
        items_per_page = 10  # sane default – plenty for a dashboard
        last_page = max(0, (total_sessions - 1) // items_per_page)  # zero-based
        query = [f"itemsPerPage={items_per_page}", f"page={last_page}"]
        if self.token:
            query.insert(0, f"token={self.token}")
        sessions_resp = self.get(f"{endpoint}?{'&'.join(query)}").json()
        sessions = sessions_resp.get("sessions", [])

        # ------------------------------------------------------------------
        # Build user-id → username mapping so dashboard shows names instead of
        # raw UUIDs.  One request is sufficient and relatively cheap.
        # ------------------------------------------------------------------
        user_name_by_id: dict[str, str] = {}
        try:
            users_json = self.get(f"{self.API_PREFIX}/users").json()
            for u in users_json.get("users", users_json):
                if isinstance(u, dict) and u.get("id"):
                    user_name_by_id[str(u["id"])] = u.get("username", "user")
        except Exception:
            # If the call fails we fall back to raw IDs – no fatal error.
            pass

        now_ms = int(time.time() * 1000)  # current time in ms (ABS uses ms)
        active: list[dict] = []

        for raw in sessions:
            if not isinstance(raw, dict):
                continue

            updated_at = raw.get("updatedAt")  # ms precision
            if updated_at is None or now_ms - updated_at > 60_000:  # > 1 min
                continue  # stale / finished session

            # --- basic metadata ------------------------------------------------
            session_id = str(raw.get("id", ""))
            user_id = str(raw.get("userId", ""))
            user_display = user_name_by_id.get(user_id, user_id)
            media_type = raw.get("mediaType", "book")
            title = raw.get("displayTitle", "Unknown")

            # --- progress ------------------------------------------------------
            pos = raw.get("currentTime", 0)  # seconds
            duration = raw.get("duration", 0) or 1  # avoid div-by-zero
            progress = max(0.0, min(1.0, pos / duration))

            # --- device / client ----------------------------------------------
            device_info = raw.get("deviceInfo", {})
            device_name = (
                f"{device_info.get('osName', '')} {device_info.get('browserName', '')}".strip()
                or "Unknown Device"
            )
            client = raw.get("mediaPlayer", "")

            # --- artwork -------------------------------------------------------

            # Primary & secondary artwork --------------------------------------
            poster_url: str | None = None
            thumb_url: str | None = None

            li_id = raw.get("libraryItemId")
            if li_id:
                # Cover endpoint (vertical poster)
                poster_url = f"{self.url}{self.API_PREFIX}/items/{li_id}/cover"

                # Try to leverage the preview/thumbnail endpoint if the server
                # version supports it.  ABS provides automatic resizing via the
                # optional width/height query params.  We keep it simple and
                # request a 400-pixel wide version which most dashboards can
                # display without additional processing.
                thumb_url = f"{poster_url}?width=400"

            # RSS image fallback – some podcast sessions won’t have a library
            # item ID.  In that case we rely on the RSS <image> URL which is
            # already a square thumbnail.
            if poster_url is None:
                meta = raw.get("mediaMetadata", {})
                poster_url = meta.get("imageUrl")
                thumb_url = poster_url

            artwork_url = poster_url

            # --- transcoding ----------------------------------------------------
            play_method = raw.get("playMethod", 0)  # 0 = direct play
            transcoding_info = {
                "is_transcoding": False,
                "direct_play": play_method == 0,
            }
            active.append(
                {
                    "user_name": user_display,
                    "media_title": title,
                    "media_type": media_type,
                    "progress": progress,
                    "state": "playing",  # ABS has no explicit pause flag yet
                    "session_id": session_id,
                    "client": client,
                    "device_name": device_name,
                    "position_ms": int(pos * 1000),
                    "duration_ms": int(duration * 1000),
                    "artwork_url": artwork_url,
                    "thumbnail_url": thumb_url,
                    "transcoding": transcoding_info,
                }
            )

        return active

    def statistics(self):
        """Return essential AudiobookShelf server statistics for the dashboard.

        Only collects data actually used by the UI:
        - Server version for health card (Unknown for ABS)
        - Active sessions count for health card
        - Transcoding sessions count for health card (always 0 for ABS)
        - Total users count for health card

        Returns:
            dict: Server statistics with minimal API calls
        """
        try:
            stats = {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
            }

            # ------------------------------------------------------------------
            # Active sessions – reuse the same pagination / freshness logic as
            # *now_playing()* so numbers stay in sync across the dashboard.
            # ------------------------------------------------------------------
            try:
                active_sessions = self.now_playing()
            except Exception as exc:
                logging.error(
                    "ABS statistics: failed to calculate active sessions – %s", exc
                )
                active_sessions = []

            # ------------------------------------------------------------------
            # User statistics – we only need total count for the health card.
            # ------------------------------------------------------------------
            total_users = 0
            try:
                users_resp = self.get(f"{self.API_PREFIX}/users").json()
                users_list = users_resp.get("users", users_resp)
                total_users = len(users_list) if isinstance(users_list, list) else 0
            except Exception as exc:
                logging.error("ABS statistics: failed to fetch users – %s", exc)

            stats["user_stats"] = {
                "total_users": total_users,
                "active_sessions": len(active_sessions),
            }

            # ------------------------------------------------------------------
            # Server statistics – ABS doesn't expose version or transcoding
            # count via the API (yet) so we fill with sane defaults.
            # ------------------------------------------------------------------
            stats["server_stats"] = {
                "version": "Unknown",
                "transcoding_sessions": 0,
            }

            return stats

        except Exception as e:
            logging.error(f"Failed to get AudiobookShelf statistics: {e}")
            return {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
                "error": str(e),
            }

    # RestApiMixin overrides -------------------------------------------------

    def _headers(self) -> dict[str, str]:  # type: ignore[override]
        """Return default headers including Authorization if a token is set."""
        headers: dict[str, str] = {"Accept": "application/json"}
        if getattr(self, "token", None):
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
