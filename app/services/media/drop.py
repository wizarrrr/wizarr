"""Drop media server integration.

Drop is a digital media management platform that provides API access for user
and invitation management through a System token with appropriate scopes.
"""

import logging
import re
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, User
from app.services.invites import is_invite_valid
from app.services.media.client_base import RestApiMixin, register_media_client

if TYPE_CHECKING:
    from app.services.media.user_details import MediaUserDetails

# Simple email validation pattern
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")


@register_media_client("drop")
class DropClient(RestApiMixin):
    """Drop media server client using System token authentication."""

    def __init__(self, *args, **kwargs):
        # Defaults for historical callers
        kwargs.setdefault("url_key", "server_url")
        kwargs.setdefault("token_key", "api_key")
        super().__init__(*args, **kwargs)

    def _headers(self) -> dict[str, str]:
        """Return authentication headers for Drop API requests."""
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.token:
            # Drop uses Bearer token authentication
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # ------------------------------------------------------------------
    # Wizarr API – libraries
    # ------------------------------------------------------------------

    def libraries(self) -> dict[str, str]:
        """Return available libraries from Drop server.

        Note: Drop doesn't have traditional libraries like Plex/Jellyfin.
        This is a placeholder implementation that returns an empty dict.
        """
        try:
            # Drop doesn't have library endpoints in the documented API
            # Return empty dict since this is required by the interface
            logging.debug("Drop: No libraries endpoint available")
            return {}
        except Exception as exc:
            logging.warning("Drop: failed to fetch libraries – %s", exc)
            return {}

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        """Scan available libraries on this Drop server.

        Args:
            url: Optional server URL override
            token: Optional API token override

        Returns:
            dict: Empty dict since Drop doesn't have traditional libraries
        """
        try:
            # Drop doesn't have library scanning functionality
            logging.debug("Drop: No library scanning available")
            return {}
        except Exception as e:
            logging.warning("Drop: failed to scan libraries – %s", e)
            return {}

    # ------------------------------------------------------------------
    # Wizarr API – users
    # ------------------------------------------------------------------

    def list_users(self) -> list[User]:
        """Sync Drop users into local DB.

        Requires the supplied API token to have 'user:read' scope.
        """
        try:
            # Get users from Drop API
            response = self.get("/api/v1/admin/users")
            remote_users: list[dict[str, Any]] = response.json()

            if not isinstance(remote_users, list):
                logging.warning(
                    "Drop: unexpected /admin/users payload: %s", remote_users
                )
                return []

            remote_by_id = {str(u.get("id")): u for u in remote_users if u.get("id")}

            # Upsert user rows in local DB
            for user_id, drop_user in remote_by_id.items():
                db_row: User | None = User.query.filter_by(
                    token=user_id, server_id=getattr(self, "server_id", None)
                ).first()

                if not db_row:
                    db_row = User(
                        token=user_id,
                        username=drop_user.get("username", "drop-user"),
                        email=drop_user.get("email", ""),
                        code="drop",  # placeholder – no invite code
                        server_id=getattr(self, "server_id", None),
                    )
                    db.session.add(db_row)
                else:
                    # Update existing user
                    db_row.username = drop_user.get("username", db_row.username)
                    db_row.email = drop_user.get("email", db_row.email)

            db.session.commit()

            # Remove local users that no longer exist upstream
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

            # Add policy attributes based on actual Drop user data
            for user in users:
                # Get the corresponding Drop user data
                drop_user = remote_by_id.get(user.token, {})

                drop_policies = {
                    # Server-specific data
                    "enabled": drop_user.get("enabled", True),
                    "admin": drop_user.get("admin", False),
                    "displayName": drop_user.get("displayName", user.username),
                    "profilePictureObjectId": drop_user.get("profilePictureObjectId"),
                    # Standardized permission keys for UI display
                    "allow_downloads": True,  # Drop supports downloads by default
                    "allow_live_tv": False,  # Drop doesn't support live TV
                    "allow_camera_upload": False,  # Drop doesn't support camera upload
                }
                user.set_raw_policies(drop_policies)

                # Update standardized User model columns
                user.allow_downloads = True  # Drop supports downloads by default
                user.allow_live_tv = False  # Drop doesn't support live TV
                user.allow_camera_upload = False  # Drop doesn't support camera upload
                user.is_admin = drop_user.get("admin", False)

            # Single commit for all metadata updates
            try:
                db.session.commit()
            except Exception as e:
                logging.error("Drop: failed to update user metadata – %s", e)
                db.session.rollback()
                return []

            return users

        except Exception as exc:
            logging.warning("Drop: failed to list users – %s", exc, exc_info=True)
            return []

    def create_user(
        self, username: str, password: str, email: str | None = None
    ) -> str:
        """Create a Drop user using the invitation system.

        Drop uses a two-step process:
        1. Create an invitation
        2. Consume the invitation to create the user
        """
        try:
            # Step 1: Create invitation
            from datetime import datetime, timedelta

            expires = datetime.now() + timedelta(hours=1)
            invitation_payload = {
                "expires": expires.isoformat() + "Z",
                "username": username,
                "email": email,
                "isAdmin": False,
            }

            invite_response = self.post(
                "/api/v1/admin/invitation", json=invitation_payload
            )
            invitation_data = invite_response.json()
            invitation_id = invitation_data.get("id")

            if not invitation_id:
                raise ValueError("No invitation ID returned from Drop API")

            # Step 2: Consume invitation to create user
            # Drop requires minimum 14 character password
            if len(password) < 14:
                password = password + "0" * (14 - len(password))

            signup_payload = {
                "invitation": invitation_id,
                "username": username,
                "password": password,
                "email": email,
                "displayName": username,
            }

            user_response = self.post("/api/v1/auth/signup/simple", json=signup_payload)
            user_data = user_response.json()

            return str(user_data.get("id", ""))

        except Exception as exc:
            if "404" in str(exc):
                raise NotImplementedError(
                    "Drop server does not support Simple Authentication. "
                    "Please enable Simple Authentication in your Drop server configuration."
                ) from exc
            logging.error("Drop: failed to create user – %s", exc)
            raise

    def update_user(self, user_id: str, patch: dict[str, Any]):
        """Update a Drop user.

        Note: Update functionality may not be available in Drop API.
        This is a placeholder implementation.
        """
        try:
            # Drop API doesn't seem to have user update endpoints in the documented API
            logging.warning("Drop: user update not implemented in API")
            return {}
        except Exception as exc:
            logging.error("Drop: failed to update user – %s", exc)
            raise

    def enable_user(self, user_id: str) -> bool:
        """Enable a user account on Drop.

        Args:
            user_id: The user's Drop ID

        Returns:
            bool: True if the user was successfully enabled, False otherwise
        """
        try:
            # Drop doesn't have a direct disable/enable feature
            # Return False to indicate this operation is not supported
            structlog.get_logger().warning("Drop does not support disabling/enabling users")
            return False
        except Exception as e:
            structlog.get_logger().error(f"Failed to enable Drop user: {e}")
            return False

    def disable_user(self, user_id: str, enable: bool = False) -> bool:
        """Disable a user account on Drop.

        Args:
            user_id: The user's Drop ID
            enable: If True, enables the user (sets IsDisabled=False). 
                If False (default), disables the user (sets IsDisabled=True).

        Returns:
            bool: True if the user was successfully disabled, False otherwise
        """
        try:
            if enable is True:
                return enable_user(self, user_id) # Enable not supported
            # Drop doesn't have a direct disable feature
            # Return False to indicate this operation is not supported
            structlog.get_logger().warning("Drop does not support disabling users")
            return False
        except Exception as e:
            action = "enable" if enable else "disable"
            structlog.get_logger().error(f"Failed to {action} Drop user: {e}")
            return False

    def delete_user(self, user_id: str):
        """Delete a Drop user."""
        try:
            resp = self.delete(f"/api/v1/admin/users/{user_id}")
            if resp.status_code not in (200, 204):
                resp.raise_for_status()
        except Exception as exc:
            logging.error("Drop: failed to delete user – %s", exc)
            raise

    def get_user(self, user_id: str) -> dict[str, Any]:
        """Get user info in legacy format for backward compatibility."""
        details = self.get_user_details(user_id)
        return {
            "id": details.user_id,
            "username": details.username,
            "email": details.email,
            "enabled": details.is_enabled,
            "created_at": details.created_at.isoformat() + "Z"
            if details.created_at
            else None,
        }

    def get_user_details(self, user_id: str) -> "MediaUserDetails":
        """Get detailed user information in standardized format."""
        from app.services.media.user_details import MediaUserDetails

        try:
            # Get raw user data from Drop API
            response = self.get(f"/api/v1/admin/users/{user_id}")
            raw_user = response.json()

            return MediaUserDetails(
                user_id=str(raw_user.get("id", user_id)),
                username=raw_user.get("username", "Unknown"),
                email=raw_user.get("email"),
                is_admin=raw_user.get("admin", False),
                is_enabled=raw_user.get("enabled", True),
                created_at=None,  # Would need to parse if available
                last_active=None,  # Not available in API
                library_access=None,  # Drop doesn't have traditional libraries - indicates full access
                raw_policies=raw_user,
            )
        except Exception as exc:
            logging.error("Drop: failed to get user details – %s", exc)
            raise

    # ------------------------------------------------------------------
    # Statistics and monitoring
    # ------------------------------------------------------------------

    def now_playing(self) -> list[dict]:
        """Return currently playing sessions.

        Note: Drop may not have session tracking functionality.
        Returns empty list as placeholder.
        """
        try:
            # Drop API doesn't seem to have session tracking endpoints
            logging.debug("Drop: No session tracking available")
            return []
        except Exception as exc:
            logging.warning("Drop: failed to get now playing – %s", exc)
            return []

    def statistics(self):
        """Return Drop server statistics for the dashboard."""
        try:
            stats = {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
            }

            # User statistics
            try:
                users_response = self.get("/api/v1/admin/users")
                users_data = users_response.json()
                stats["user_stats"] = {
                    "total_users": len(users_data)
                    if isinstance(users_data, list)
                    else 0,
                    "active_sessions": 0,  # No session tracking
                }
            except Exception as e:
                logging.error(f"Failed to get Drop user stats: {e}")
                stats["user_stats"] = {"total_users": 0, "active_sessions": 0}

            # Server statistics
            try:
                # Test API connectivity
                self.get("/api/v1/user")
                stats["server_stats"] = {
                    "version": "Unknown",  # Drop doesn't expose version in documented API
                    "transcoding_sessions": 0,  # Drop doesn't transcode
                }
            except Exception as e:
                logging.error(f"Failed to get Drop server stats: {e}")
                stats["server_stats"] = {
                    "version": "Unknown",
                    "transcoding_sessions": 0,
                }

            return stats

        except Exception as e:
            logging.error(f"Failed to get Drop statistics: {e}")
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
                # Fallback for legacy settings
                servers = MediaServer.query.filter_by(server_type="drop").all()
                if servers:
                    server_ids = [s.id for s in servers]
                    count = User.query.filter(User.server_id.in_(server_ids)).count()
                else:
                    count = 0
            return count
        except Exception as e:
            logging.error(f"Failed to get Drop user count from database: {e}")
            return 0

    def get_server_info(self) -> dict:
        """Get lightweight server information without triggering user sync."""
        try:
            return {
                "version": "Unknown",  # Would need API call to get version
                "transcoding_sessions": 0,  # Drop doesn't transcode
                "active_sessions": 0,  # Would need session tracking
            }
        except Exception as e:
            logging.error(f"Failed to get Drop server info: {e}")
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
            logging.error(f"Failed to get Drop readonly statistics: {e}")
            return {
                "user_stats": {"total_users": 0, "active_sessions": 0},
                "server_stats": {"version": "Unknown", "transcoding_sessions": 0},
                "library_stats": {},
                "content_stats": {},
                "error": str(e),
            }

    # ------------------------------------------------------------------
    # Public sign-up via invites
    # ------------------------------------------------------------------

    def _do_join(
        self,
        username: str,
        password: str,
        confirm: str,
        email: str,
        code: str,
    ) -> tuple[bool, str]:
        """Handle public sign-up via invite for Drop servers."""

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
            # Create user via Drop's invitation system
            user_id = self.create_user(username, password, email=email)

            # Get invitation for expiry calculation
            inv = Invitation.query.filter_by(code=code).first()

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

        except Exception:
            logging.error("Drop join error", exc_info=True)
            db.session.rollback()
            return False, "An unexpected error occurred."
