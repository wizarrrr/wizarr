from __future__ import annotations

import base64
import datetime
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.media.user_details import MediaUserDetails

import requests
from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, User
from app.services.invites import is_invite_valid

from .client_base import RestApiMixin, register_media_client

"""Romm media‐server client.

This minimal implementation lets Wizarr recognise RomM as a media‐server
backend so that an admin can store RomM connection credentials, scan the
list of *platforms* (treated as "libraries"), and present basic read‐only
user information in the UI.

NOTE – RomM exposes a comprehensive HTTP API that is documented via
OpenAPI (see /api/docs on any RomM instance).  To keep the initial
integration small we only implement the endpoints that Wizarr currently
needs:

    * GET /api/platforms  –>  list of platforms (= libraries)
    * GET /api/users      –>  list all users (admin only)


"""

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

# Simple e-mail validation (same pattern as other clients)
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")


@register_media_client("romm")
class RommClient(RestApiMixin):
    """Very small wrapper around the RomM REST API."""

    API_PREFIX = "/api"

    def __init__(self, *args, **kwargs):
        # Defaults for historical callers
        kwargs.setdefault("url_key", "server_url")
        kwargs.setdefault("token_key", "api_key")
        super().__init__(*args, **kwargs)

    def _headers(self) -> dict[str, str]:  # type: ignore[override]
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Basic {self.token}"
        return headers

    # ------------------------------------------------------------------
    # Wizarr API – libraries
    # ------------------------------------------------------------------

    def libraries(self) -> dict[str, str]:
        """Return mapping of platform_id → display_name."""
        try:
            response = self.get(f"{self.API_PREFIX}/platforms")
            data: list[dict[str, Any]] = response.json()
            return {p["id"]: p.get("name", p["id"]) for p in data}
        except Exception as exc:
            logging.warning("RomM: failed to fetch platforms – %s", exc)
            return {}

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        """Scan available platforms on this RomM server.

        Args:
            url: Optional server URL override
            token: Optional API token override

        Returns:
            dict: Platform name -> platform ID mapping
        """
        try:
            if url and token:
                # RomM uses basic auth with token as password
                auth_header = base64.b64encode(f"admin:{token}".encode()).decode()
                headers = {"Authorization": f"Basic {auth_header}"}
                response = requests.get(
                    f"{url.rstrip('/')}/api/platforms", headers=headers, timeout=10
                )
                response.raise_for_status()
                data = response.json()
            else:
                # Use saved credentials
                response = self.get(f"{self.API_PREFIX}/platforms")
                data = response.json()

            return {p.get("name", p["id"]): p["id"] for p in data}
        except Exception as e:
            logging.warning("RomM: failed to scan platforms – %s", e)
            return {}

    # ------------------------------------------------------------------
    # Wizarr API – users (read-only)
    # ------------------------------------------------------------------

    def list_users(self) -> list[User]:
        """Sync RomM users into local DB (read-only).

        Requires the supplied API token to belong to a RomM *admin* user as
        `/api/users` is admin-only.
        """
        # RomM supports pagination via ?skip= & take= parameters.  We fetch in
        # chunks of *take*=100 until the returned set is smaller than the
        # requested size, indicating we've reached the end.

        remote_users: list[dict[str, Any]] = []
        skip, take = 0, 100
        try:
            while True:
                r = self.get(
                    f"{self.API_PREFIX}/users", params={"skip": skip, "take": take}
                )
                batch: list[dict[str, Any]] = r.json()
                # Some RomM versions wrap the list in {"items": [...]} – handle both.
                if isinstance(batch, dict) and "items" in batch:
                    batch = batch["items"]  # type: ignore[assignment]

                if not isinstance(batch, list):
                    logging.warning("ROMM: unexpected /users payload: %s", batch)
                    break

                remote_users.extend(batch)

                if len(batch) < take:
                    break  # reached final page
                skip += take
        except Exception as exc:  # noqa: BLE001
            logging.warning("ROMM: failed to list users – %s", exc, exc_info=True)
            return []

        remote_by_id = {str(u.get("id") or u["username"]): u for u in remote_users}

        # 1) upsert basic user rows so Wizarr UI has something to show
        for romm_id, ru in remote_by_id.items():
            db_row: User | None = User.query.filter_by(
                token=romm_id, server_id=getattr(self, "server_id", None)
            ).first()
            if not db_row:
                db_row = User(
                    token=romm_id,
                    username=ru.get("username", "romm-user"),
                    email=ru.get("email", ""),
                    code="romm",  # placeholder – no invite code
                    password="romm",  # placeholder
                    server_id=getattr(self, "server_id", None),
                )
                db.session.add(db_row)
            else:
                db_row.username = ru.get("username", db_row.username)
                db_row.email = ru.get("email", db_row.email)
        db.session.commit()

        # 2) Remove local users that no longer exist upstream
        for local in User.query.filter(
            User.server_id == getattr(self, "server_id", None)
        ).all():
            if local.token not in remote_by_id:
                db.session.delete(local)
        db.session.commit()

        # Get users with default policy information
        users = User.query.filter(
            User.server_id == getattr(self, "server_id", None)
        ).all()

        # Add default policy attributes (RomM doesn't have specific download/live TV policies)
        for user in users:
            user.allow_downloads = True  # Default to True for gaming apps
            user.allow_live_tv = False  # RomM doesn't have Live TV
            user.allow_sync = True  # Default to True for gaming apps

        return users

    # ------------------------------------------------------------------
    # Un-implemented mutating operations
    # ------------------------------------------------------------------

    # Even though Wizarr currently doesn't expose UI to mutate RomM users, we
    # provide simple wrappers so future work (or API consumers) can call them.

    def create_user(
        self, username: str, password: str, email: str | None = None
    ) -> str:
        """Create a RomM user and return the new ``user_id``.

        Only *username* and *password* are mandatory according to RomM docs.
        """
        payload: dict[str, Any] = {
            "username": username,
            "password": password,
            "email": email,
            "role": "VIEWER",
        }

        # ------------------------------------------------------------------
        # Attempt 1 – query-string parameters (matches observed RomM behaviour)
        # ------------------------------------------------------------------
        try:
            r = self.post(f"{self.API_PREFIX}/users", params=payload)
        except requests.HTTPError as exc:
            r = exc.response  # type: ignore[assignment]

        # If the server expects JSON body instead, fall back once
        if r is not None and r.status_code == 422:
            try:
                logging.warning(
                    "ROMM create_user validation error (params): %s", r.json()
                )
            except Exception:
                logging.warning(
                    "ROMM create_user validation 422 (params) with non-JSON body: %s",
                    r.text,
                )

            alt = payload.copy()
            alt["passwordConfirm"] = password  # older builds require this field

            try:
                r = self.post(f"{self.API_PREFIX}/users", json=alt)
            except requests.HTTPError as exc:
                r = exc.response  # type: ignore[assignment]

        data: dict[str, Any] = {}
        try:
            if r is not None:
                data = r.json()
        except Exception:
            pass

        return data.get("id") or data.get("user", {}).get("id")  # type: ignore[return-value]

    def update_user(self, user_id: str, patch: dict[str, Any]):
        """PATCH selected fields on a RomM user object."""
        return self.patch(f"{self.API_PREFIX}/users/{user_id}", json=patch).json()

    def delete_user(self, user_id: str):
        resp = self.delete(f"{self.API_PREFIX}/users/{user_id}")
        if resp.status_code not in (200, 204):
            resp.raise_for_status()

    def get_user(self, user_id: str) -> dict[str, Any]:
        """Get user info in legacy format for backward compatibility."""
        details = self.get_user_details(user_id)
        return {
            "id": details.user_id,
            "username": details.username,
            "email": details.email,
            "role": "ADMIN" if details.is_admin else "VIEWER",
            "enabled": details.is_enabled,
            "created_at": details.created_at.isoformat() + "Z"
            if details.created_at
            else None,
        }

    def get_user_details(self, user_id: str) -> MediaUserDetails:
        """Get detailed user information in standardized format."""
        from app.models import Library
        from app.services.media.user_details import MediaUserDetails, UserLibraryAccess

        # Get raw user data from RomM API
        r = self.get(f"{self.API_PREFIX}/users/{user_id}")
        raw_user = r.json()

        # Get all available libraries for this server since RomM gives full access
        libs_q = (
            Library.query.filter_by(server_id=self.server_id, enabled=True)
            .order_by(Library.name)
            .all()
        )
        library_access = [
            UserLibraryAccess(
                library_id=lib.external_id, library_name=lib.name, has_access=True
            )
            for lib in libs_q
        ]

        return MediaUserDetails(
            user_id=str(raw_user.get("id", user_id)),
            username=raw_user.get("username", "Unknown"),
            email=raw_user.get("email"),
            is_admin=raw_user.get("role") == "ADMIN",
            is_enabled=raw_user.get("enabled", True),
            created_at=datetime.datetime.fromisoformat(
                raw_user["created_at"].rstrip("Z")
            )
            if raw_user.get("created_at")
            else None,
            last_active=None,  # RomM doesn't track last active time
            library_access=library_access,
            raw_policies=raw_user,
        )

    # ------------------------------------------------------------------
    # Public sign-up via invites (same contract as other clients)
    # ------------------------------------------------------------------

    def _password_for_db(self, password: str) -> str:
        """Return value stored in local DB for the given raw password."""
        return password  # no hashing for now – keep consistent with other svc

    def now_playing(self) -> list[dict]:
        """Return a list of currently playing sessions from RomM.

        Note: RomM is a ROM/game collection management server that does not
        provide session tracking or "now playing" functionality in its API.
        This method always returns an empty list.

        Returns:
            list: Always returns an empty list since RomM doesn't track active sessions.
        """
        # RomM API doesn't provide session/now-playing endpoints
        # It's focused on ROM collection management, not active gaming sessions
        logging.debug(
            "ROMM: No session tracking available - RomM doesn't provide now-playing functionality"
        )
        return []

    def statistics(self):
        """Return essential RomM server statistics for the dashboard.

        Only collects data actually used by the UI:
        - Server version for health card (Unknown for RomM)
        - Active sessions count for health card (always 0 for RomM)
        - Transcoding sessions count for health card (always 0 for RomM)
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

            # User statistics - only what's displayed in UI
            try:
                users_response = self.get(f"{self.API_PREFIX}/users").json()
                stats["user_stats"] = {
                    "total_users": len(users_response),
                    "active_sessions": 0,  # RomM doesn't have sessions concept
                }
            except Exception as e:
                logging.error(f"Failed to get RomM user stats: {e}")
                stats["user_stats"] = {"total_users": 0, "active_sessions": 0}

            # Server statistics - minimal data
            try:
                stats["server_stats"] = {
                    "version": "Unknown",  # RomM doesn't expose version via API
                    "transcoding_sessions": 0,  # RomM doesn't transcode
                }
            except Exception as e:
                logging.error(f"Failed to get RomM server stats: {e}")
                stats["server_stats"] = {}

            return stats

        except Exception as e:
            logging.error(f"Failed to get RomM statistics: {e}")
            return {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
                "error": str(e),
            }

    def _do_join(
        self,
        username: str,
        password: str,
        confirm: str,
        email: str,
        code: str,
    ) -> tuple[bool, str]:
        """Handle public sign-up via invite for RomM servers."""

        if not EMAIL_RE.fullmatch(email):
            return False, "Invalid e-mail address."
        if not 8 <= len(password) <= 128:
            return False, "Password must be 8–128 characters."
        if password != confirm:
            return False, "Passwords do not match."

        ok, msg = is_invite_valid(code)
        if not ok:
            return False, msg

        existing = User.query.filter(
            or_(User.username == username, User.email == email),
            User.server_id == getattr(self, "server_id", None),
        ).first()
        if existing:
            return False, "User or e-mail already exists."

        try:
            # 1) create remotely – RomM returns the new user ID
            user_id = self.create_user(username, password, email=email)

            # 2) Determine which libraries (platforms) this invite grants
            inv = Invitation.query.filter_by(code=code).first()

            # Currently RomM doesn't expose per-platform permissions in API
            # (viewers can see everything).  We therefore don't attempt to
            # filter library access yet – we only need the DB linkage.

            from app.services.expiry import calculate_user_expiry

            expires = (
                calculate_user_expiry(inv, getattr(self, "server_id", None))
                if inv
                else None
            )

            self._create_user_with_identity_linking(
                {
                    "username": username,
                    "email": email,
                    "token": user_id,
                    "code": code,
                    "expires": expires,
                    "server_id": getattr(self, "server_id", None),
                }
            )
            db.session.commit()

            return True, ""

        except Exception:  # noqa: BLE001
            logging.error("ROMM join error", exc_info=True)
            db.session.rollback()
            return False, "An unexpected error occurred."
