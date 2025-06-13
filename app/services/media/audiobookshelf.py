from __future__ import annotations

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

import logging
from typing import Any, Dict, List
import re

import requests

from app.extensions import db
from app.models import User, Invitation, Library
from .client_base import MediaClient, register_media_client


@register_media_client("audiobookshelf")
class AudiobookshelfClient(MediaClient):
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
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _headers(self) -> Dict[str, str]:
        """Return default headers incl. auth token (if set)."""
        hdrs: Dict[str, str] = {}
        if self.token:
            hdrs["Authorization"] = f"Bearer {self.token}"
        return hdrs

    def _get(self, path: str):
        """GET ``path`` relative to the server root.

        Raises ``requests.HTTPError`` on non-2xx so the caller can handle
        it in a single place.
        """
        url = f"{self.url}{path}"
        logging.info("ABS GET  %s", url)
        resp = requests.get(url, headers=self._headers, timeout=10)
        resp.raise_for_status()
        return resp

    # ------------------------------------------------------------------
    # Public API expected by Wizarr
    # ------------------------------------------------------------------

    # --- libraries -----------------------------------------------------

    def libraries(self) -> Dict[str, str]:
        """Return mapping of ``library_id`` → ``display_name``.

        Audiobookshelf exposes ``GET /api/libraries`` which returns
        ``{"libraries": [ … ]}``.
        """
        try:
            data = self._get(f"{self.API_PREFIX}/libraries").json()
            # May have drilldown or direct list depending on ABS version
            libs = data.get("libraries", data)
            return {item["id"]: item["name"] for item in libs}
        except Exception as exc:
            logging.warning("ABS: failed to fetch libraries – %s", exc)
            return {}

    # --- users ---------------------------------------------------------

    def list_users(self) -> List[User]:
        """Read users from Audiobookshelf and reflect them locally.

        At the moment we *only* sync users that already exist in the
        local DB.  Creating new users and managing their permissions is
        still on the TODO list.
        """
        try:
            data = self._get(f"{self.API_PREFIX}/users").json()
            raw_users: List[Dict[str, Any]] = data.get("users", data)  # ABS may wrap list in {"users": [...]}
        except Exception as exc:
            logging.warning("ABS: failed to list users – %s", exc)
            return []

        # Index by ABS user‐id for quick lookups
        raw_by_id = {u["id"]: u for u in raw_users}

        # ------------------------------------------------------------------
        # 1) Add new users or update basic fields so the UI has fresh data
        # ------------------------------------------------------------------
        for uid, remote in raw_by_id.items():
            db_row = (
                User.query
                .filter_by(token=uid, server_id=getattr(self, "server_id", None))
                .first()
            )
            if not db_row:
                db_row = User(
                    token=uid,
                    username=remote.get("username", "abs-user"),
                    email=remote.get("email", ""),
                    code="empty",  # placeholder – signifies "no invite code"
                    password="abs",  # placeholder
                    server_id=getattr(self, "server_id", None),
                )
                db.session.add(db_row)
            else:
                # Simple field refresh (username/email might have changed)
                db_row.username = remote.get("username", db_row.username)
                db_row.email = remote.get("email", db_row.email)

        db.session.commit()

        # ------------------------------------------------------------------
        # 2) Remove local users that have disappeared upstream.  This keeps
        #    the Wizarr DB in sync so "ghost" accounts don't show up as
        #    "Local" after they were deleted on the ABS server.
        # ------------------------------------------------------------------
        to_check = (
            User.query
            .filter(User.server_id == getattr(self, "server_id", None))
            .all()
        )
        for local in to_check:
            if local.token not in raw_by_id:
                db.session.delete(local)

        db.session.commit()

        return (
            User.query
            .filter(User.server_id == getattr(self, "server_id", None))
            .all()
        )

    # --- user management ------------------------------------------------

    def create_user(self, username: str, password: str, email: str,  *, is_admin: bool = False) -> str:
        """Create a user and return the Audiobookshelf user‐ID.

        The ABS API expects at least ``username``.  A password can be an
        empty string (guest), but Wizarr always passes one.
        """
        payload = {
            "username": username,
            "password": password,
            "isActive": True,
            "email": email,
            "type": "admin" if is_admin else "user",
        }
        resp = requests.post(
            f"{self.url}{self.API_PREFIX}/users",
            json=payload,
            headers=self._headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        uid = data.get("id") or data.get("user", {}).get("id")
        return uid

    def update_user(self, user_id: str, payload: Dict[str, Any]):
        """PATCH arbitrary fields on a user object."""
        resp = requests.patch(
            f"{self.url}{self.API_PREFIX}/users/{user_id}",
            json=payload,
            headers=self._headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def delete_user(self, user_id: str):
        """Delete a user permanently from Audiobookshelf."""
        resp = requests.delete(
            f"{self.url}{self.API_PREFIX}/users/{user_id}",
            headers=self._headers,
            timeout=10,
        )
        # 204 No Content or 200
        if resp.status_code not in (200, 204):
            resp.raise_for_status()

    def get_user(self, user_id: str):
        """Return a full user object from Audiobookshelf."""
        return self._get(f"{self.API_PREFIX}/users/{user_id}").json()

    # ------------------------------------------------------------------
    # Public sign-up (invite links)
    # ------------------------------------------------------------------

    def _password_for_db(self, password: str) -> str:
        """Return the password value to store in the local DB (plain)."""
        return password

    @staticmethod
    def _mark_invite_used(inv, user):
        inv.used = True if not inv.unlimited else inv.used
        inv.used_at = db.func.now()
        inv.used_by = user
        db.session.commit()

    def _set_specific_libraries(self, user_id: str, library_ids: List[str]):
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
        perms["accessAllLibraries"] = False if library_ids else True

        patch = {
            "permissions": perms,
            # Root-level list of library IDs that the user may access
            "librariesAccessible": library_ids if library_ids else [],
        }

        try:
            self.update_user(user_id, patch)
        except Exception:
            logging.exception("ABS: failed to update permissions for %s", user_id)

    def join(self, username: str, password: str, confirm: str, email: str, code: str):
        """Public invite flow for Audiobookshelf users."""
        from sqlalchemy import or_
        from app.services.invites import is_invite_valid
        from app.models import Invitation, User

        if not self.EMAIL_RE.fullmatch(email):
            return False, "Invalid e-mail address."
        if not 8 <= len(password) <= 20:
            return False, "Password must be 8–20 characters."
        if password != confirm:
            return False, "Passwords do not match."

        ok, msg = is_invite_valid(code)
        if not ok:
            return False, msg

        existing = User.query.filter(
            or_(User.username == username, User.email == email),
            User.server_id == getattr(self, "server_id", None)
        ).first()
        if existing:
            return False, "User or e-mail already exists."

        try:
            user_id = self.create_user(username, password, email=email)
            if not user_id:
                return False, "Audiobookshelf did not return a user id – please verify the server URL/token."
            inv = Invitation.query.filter_by(code=code).first()

            # ------------------------------------------------------------------
            # 1) Restrict library access (if requested)
            # ------------------------------------------------------------------
            if inv.libraries:
                # Use libraries tied to the invite
                lib_ids = [lib.external_id for lib in inv.libraries]
            else:
                # Fallback to all *enabled* libraries for this server
                lib_ids = [
                    lib.external_id
                    for lib in Library.query.filter_by(
                        enabled=True,
                        server_id=inv.server.id if inv.server else None,
                    ).all()
                ]

            # Apply the permission patch – empty list → all libraries
            self._set_specific_libraries(user_id, lib_ids)

            # ------------------------------------------------------------------
            # 2) Calculate expiry time (optional duration on invite)
            # ------------------------------------------------------------------
            import datetime as _dt

            expires = None
            if inv.duration:
                try:
                    expires = _dt.datetime.utcnow() + _dt.timedelta(days=int(inv.duration))
                except Exception:
                    logging.warning("ABS: invalid duration on invite %s", inv.code)

            # ------------------------------------------------------------------
            # 3) Store locally
            # ------------------------------------------------------------------
            local = User(
                token=user_id,
                username=username,
                email=email,
                code=code,
                password=self._password_for_db(password),
                expires=expires,
                server_id=getattr(self, "server_id", None),
            )
            db.session.add(local)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                logging.exception("ABS join failed during DB commit")
                return False, "Internal error while saving the account."

            # 4) mark invite used
            self._mark_invite_used(inv, local)

            return True, ""
        except Exception as exc:
            logging.error("ABS join failed: %s", exc, exc_info=True)
            return False, "Failed to create user – please contact the admin." 