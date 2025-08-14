import datetime
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.media.user_details import MediaUserDetails

import requests
from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, Library, User
from app.services.invites import is_invite_valid

from .client_base import RestApiMixin, register_media_client

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")


@register_media_client("komga")
class KomgaClient(RestApiMixin):
    """Wrapper around the Komga REST API using credentials from Settings."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("url_key", "server_url")
        kwargs.setdefault("token_key", "api_key")
        super().__init__(*args, **kwargs)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def libraries(self) -> dict[str, str]:
        """Return mapping of library_id -> library_name."""
        try:
            response = self.get("/api/v1/libraries")
            libraries = response.json()
            return {lib["id"]: lib["name"] for lib in libraries}
        except Exception as e:
            logging.error(f"Failed to get Komga libraries: {e}")
            return {}

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        """Scan available libraries on this Komga server.

        Args:
            url: Optional server URL override
            token: Optional API token override

        Returns:
            dict: Library name -> library ID mapping
        """
        try:
            if url and token:
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get(
                    f"{url.rstrip('/')}/api/v1/libraries", headers=headers, timeout=10
                )
                response.raise_for_status()
                libraries = response.json()
            else:
                response = self.get("/api/v1/libraries")
                libraries = response.json()

            return {lib["name"]: lib["id"] for lib in libraries}
        except Exception as exc:
            logging.warning("Komga: failed to scan libraries – %s", exc)
            return {}

    def create_user(self, username: str, password: str, email: str) -> str:
        """Create a new Komga user and return the user ID."""
        payload = {"email": email, "password": password, "roles": ["USER"]}
        response = self.post("/api/v1/users", json=payload)
        return response.json()["id"]

    def update_user(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update a Komga user."""
        response = self.patch(f"/api/v1/users/{user_id}", json=updates)
        return response.json()

    def delete_user(self, user_id: str) -> None:
        """Delete a Komga user."""
        self.delete(f"/api/v1/users/{user_id}")

    def get_user(self, user_id: str) -> dict[str, Any]:
        """Get user info in legacy format for backward compatibility."""
        details = self.get_user_details(user_id)
        return {
            "id": details.user_id,
            "email": details.email,
            "username": details.username,
            "roles": ["ADMIN"] if details.is_admin else ["USER"],
            "createdDate": details.created_at.isoformat() + "Z"
            if details.created_at
            else None,
            "lastActiveDate": details.last_active.isoformat() + "Z"
            if details.last_active
            else None,
        }

    def get_user_details(self, user_id: str) -> "MediaUserDetails":
        """Get detailed user information in standardized format."""
        from app.models import Library
        from app.services.media.user_details import MediaUserDetails, UserLibraryAccess

        # Get raw user data from Komga API
        response = self.get(f"/api/v1/users/{user_id}")
        raw_user = response.json()

        # Get all available libraries for this server since Komga gives full access
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
            user_id=user_id,
            username=raw_user.get("email", "Unknown"),  # Komga uses email as username
            email=raw_user.get("email"),
            is_admin="ADMIN" in raw_user.get("roles", []),
            is_enabled=True,  # Komga doesn't have a disabled state in API
            created_at=datetime.datetime.fromisoformat(
                raw_user["createdDate"].rstrip("Z")
            )
            if raw_user.get("createdDate")
            else None,
            last_active=datetime.datetime.fromisoformat(
                raw_user["lastActiveDate"].rstrip("Z")
            )
            if raw_user.get("lastActiveDate")
            else None,
            library_access=library_access,
            raw_policies=raw_user,
        )

    def list_users(self) -> list[User]:
        """Sync users from Komga into the local DB and return the list of User records."""
        try:
            response = self.get("/api/v1/users")
            komga_users = {u["id"]: u for u in response.json()}

            for komga_user in komga_users.values():
                existing = User.query.filter_by(token=komga_user["id"]).first()
                if not existing:
                    new_user = User(
                        token=komga_user["id"],
                        username=komga_user["email"],
                        email=komga_user["email"],
                        code="empty",
                        server_id=getattr(self, "server_id", None),
                    )
                    db.session.add(new_user)
            db.session.commit()

            to_check = User.query.filter(
                User.server_id == getattr(self, "server_id", None)
            ).all()
            for db_user in to_check:
                if db_user.token not in komga_users:
                    db.session.delete(db_user)
            db.session.commit()

            # Get users with default policy information
            users = User.query.filter(
                User.server_id == getattr(self, "server_id", None)
            ).all()

            # Add default policy attributes (Komga doesn't have specific download/live TV policies)
            for user in users:
                user.allow_downloads = True  # Default to True for reading apps
                user.allow_live_tv = False  # Komga doesn't have Live TV
                user.allow_sync = True  # Default to True for reading apps

            return users
        except Exception as e:
            logging.error(f"Failed to list Komga users: {e}")
            return []

    def _set_library_access(self, user_id: str, library_ids: list[str]) -> None:
        """Set library access for a user."""
        if not library_ids:
            return

        try:
            for library_id in library_ids:
                self.put(f"/api/v1/users/{user_id}/shared-libraries/{library_id}")
        except Exception as e:
            logging.warning(f"Failed to set library access for user {user_id}: {e}")

    def _do_join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
        """Handle public sign-up via invite for Komga servers."""
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
            user_id = self.create_user(username, password, email)

            inv = Invitation.query.filter_by(code=code).first()

            current_server_id = getattr(self, "server_id", None)
            if inv and inv.libraries:
                library_ids = [
                    lib.external_id
                    for lib in inv.libraries
                    if lib.server_id == current_server_id
                ]
            else:
                library_ids = [
                    lib.external_id
                    for lib in Library.query.filter_by(
                        enabled=True, server_id=current_server_id
                    ).all()
                ]

            self._set_library_access(user_id, library_ids)

            from app.services.expiry import calculate_user_expiry

            expires = calculate_user_expiry(inv, current_server_id) if inv else None

            self._create_user_with_identity_linking(
                {
                    "username": username,
                    "email": email,
                    "token": user_id,
                    "code": code,
                    "expires": expires,
                    "server_id": current_server_id,
                }
            )
            db.session.commit()

            return True, ""

        except Exception:
            logging.error("Komga join error", exc_info=True)
            db.session.rollback()
            return False, "An unexpected error occurred."

    def now_playing(self) -> list[dict[str, Any]]:
        """Return a list of currently playing sessions from Komga.

        Note: Komga is a comic/manga server and doesn't provide session
        tracking or "now playing" functionality like media streaming servers.
        This method always returns an empty list.

        Returns:
            list: Always returns an empty list since Komga doesn't track active sessions.
        """
        logging.debug(
            "Komga: No session tracking available - Komga doesn't provide now-playing functionality"
        )
        return []

    def statistics(self) -> dict[str, Any]:
        """Return essential Komga server statistics for the dashboard.

        Only collects data actually used by the UI:
        - Server version for health card
        - Active sessions count for health card (always 0 for Komga)
        - Transcoding sessions count for health card (always 0 for Komga)
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
                users_response = self.get("/api/v1/users").json()
                stats["user_stats"] = {
                    "total_users": len(users_response),
                    "active_sessions": 0,  # Komga doesn't have active sessions concept
                }
            except Exception as e:
                logging.error(f"Failed to get Komga user stats: {e}")
                stats["user_stats"] = {"total_users": 0, "active_sessions": 0}

            # Server statistics - only version
            try:
                actuator_response = self.get("/api/v1/actuator/info").json()
                stats["server_stats"] = {
                    "version": actuator_response.get("build", {}).get(
                        "version", "Unknown"
                    ),
                    "transcoding_sessions": 0,  # Komga doesn't transcode
                }
            except Exception as e:
                logging.error(f"Failed to get Komga server stats: {e}")
                stats["server_stats"] = {}

            return stats

        except Exception as e:
            logging.error(f"Failed to get Komga statistics: {e}")
            return {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
                "error": str(e),
            }
