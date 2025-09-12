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
        from app.services.media.utils import (
            DateHelper,
            LibraryAccessHelper,
            StandardizedPermissions,
            create_standardized_user_details,
        )

        # Get raw user data from Komga API
        response = self.get(f"/api/v1/users/{user_id}")
        raw_user = response.json()

        # Extract permissions using utility
        permissions = StandardizedPermissions.for_basic_server(
            "komga",
            is_admin="ADMIN" in raw_user.get("roles", []),
            allow_downloads=True,  # Comic reader allows downloads
        )

        # Komga gives full access to all libraries
        library_access = LibraryAccessHelper.create_full_access()

        # Parse dates
        created_at = DateHelper.parse_iso_date(raw_user.get("createdDate"))
        last_active = DateHelper.parse_iso_date(raw_user.get("lastActiveDate"))

        return create_standardized_user_details(
            user_id=user_id,
            username=raw_user.get("email", "Unknown"),  # Komga uses email as username
            email=raw_user.get("email"),
            permissions=permissions,
            library_access=library_access,
            raw_policies=raw_user,
            created_at=created_at,
            last_active=last_active,
            is_enabled=True,  # Komga doesn't have a disabled state in API
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
                # Store both server-specific and standardized keys in policies dict
                komga_policies = {
                    # Server-specific data (Komga user info would go here)
                    "enabled": True,  # Komga users are enabled by default
                    # Standardized permission keys for UI display
                    "allow_downloads": True,  # Default to True for reading apps
                    "allow_live_tv": False,  # Komga doesn't have Live TV
                    "allow_sync": True,  # Default to True for reading apps
                }
                user.set_raw_policies(komga_policies)

            # Single commit for all metadata updates
            try:
                db.session.commit()
            except Exception as e:
                logging.error("Komga: failed to update user metadata – %s", e)
                db.session.rollback()
                return []

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

    def get_user_count(self) -> int:
        """Get lightweight user count from database without triggering sync."""
        try:
            from app.models import MediaServer, User

            if hasattr(self, "server_id") and self.server_id:
                count = User.query.filter_by(server_id=self.server_id).count()
            else:
                # Fallback for legacy settings: find MediaServer for this server type
                servers = MediaServer.query.filter_by(server_type="komga").all()
                if servers:
                    server_ids = [s.id for s in servers]
                    count = User.query.filter(User.server_id.in_(server_ids)).count()
                else:
                    # Ultimate fallback: API call
                    try:
                        users = self.get("/api/v1/users").json()
                        count = len(users) if isinstance(users, list) else 0
                    except Exception as api_error:
                        logging.warning(f"Komga API fallback failed: {api_error}")
                        count = 0
            return count
        except Exception as e:
            logging.error(f"Failed to get Komga user count from database: {e}")
            return 0

    def get_server_info(self) -> dict:
        """Get lightweight server information without triggering user sync."""
        try:
            try:
                actuator_response = self.get("/actuator/info").json()
                version = actuator_response.get("build", {}).get("version", "Unknown")
            except Exception as e:
                logging.warning(f"Failed to get Komga server info: {e}")
                version = "Unknown"

            return {
                "version": version,
                "transcoding_sessions": 0,  # Komga doesn't transcode
                "active_sessions": 0,  # Would need to implement session tracking
            }
        except Exception as e:
            logging.error(f"Failed to get Komga server info: {e}")
            return {
                "version": "Unknown",
                "transcoding_sessions": 0,
                "active_sessions": 0,
            }

    def get_readonly_statistics(self) -> dict:
        """Get lightweight statistics without triggering user synchronization."""
        try:
            user_count = self.get_user_count()
            server_info = self.get_server_info()

            return {
                "user_stats": {
                    "total_users": user_count,
                    "active_sessions": server_info.get("active_sessions", 0),
                },
                "server_stats": {
                    "version": server_info.get("version", "Unknown"),
                    "transcoding_sessions": server_info.get("transcoding_sessions", 0),
                },
                "library_stats": {},
                "content_stats": {},
            }
        except Exception as e:
            logging.error(f"Failed to get Komga readonly statistics: {e}")
            return {
                "user_stats": {"total_users": 0, "active_sessions": 0},
                "server_stats": {"version": "Unknown", "transcoding_sessions": 0},
                "library_stats": {},
                "content_stats": {},
                "error": str(e),
            }
