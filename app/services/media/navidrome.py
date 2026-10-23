from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, User
from app.services.invites import is_invite_valid
from app.services.media.utils import DateHelper, StandardizedPermissions

from .client_base import RestApiMixin, register_media_client

if TYPE_CHECKING:
    from app.services.media.user_details import MediaUserDetails


@register_media_client("navidrome")
class NavidromeClient(RestApiMixin):
    """Navidrome wrapper using Navidrome's native JSON API."""

    @classmethod
    def check_connection(
        cls, url: str, token: str, username: str | None = None
    ) -> tuple[bool, str]:
        from app.services.servers import check_navidrome

        return check_navidrome(url, token, username=username)

    def __init__(self, *args, **kwargs):
        # Provide defaults for legacy compatibility
        kwargs.setdefault("url_key", "server_url")
        kwargs.setdefault("token_key", "api_key")

        super().__init__(*args, **kwargs)

        # Normalize URL and retain the per-server administrator username.
        if self.url:
            self.url = self.url.rstrip("/")
        server_row = getattr(self, "server_row", None)
        self.username = getattr(server_row, "server_username", None) or "admin"

    def _ensure_auth(self) -> None:
        """Authenticate to Navidrome's native JSON API and cache its JWT."""
        if getattr(self, "_native_token", None):
            return
        if not self.url or not self.token:
            raise ValueError("Navidrome URL and administrator password are required")
        response = self.post("/api/auth/login", json={"username": self.username, "password": self.token}, headers={"Content-Type": "application/json"})
        native_token = response.json().get("token")
        if not native_token:
            raise ValueError("Navidrome native API login did not return a token")
        self._native_token = native_token

    def _api_request(self, method: str, endpoint: str, payload: dict | None = None):
        """Call Navidrome's native /api JSON API using its JWT auth header."""
        self._ensure_auth()
        kwargs = {"headers": {"X-ND-Authorization": f"Bearer {self._native_token}", "X-ND-Client-Unique-Id": "wizarr"}}
        if payload is not None:
            kwargs["json"] = payload
        response = self._request(method, f"/api/{endpoint.lstrip('/')}", **kwargs)
        refreshed = response.headers.get("X-ND-Authorization")
        if refreshed:
            self._native_token = refreshed.removeprefix("Bearer ").strip()
        return response

    def validate_connection(self) -> tuple[bool, str]:
        """Validate administrator access through Navidrome's native API."""
        try:
            self._api_request("GET", "user")
            return True, "Connection successful"
        except Exception as exc:
            logging.error("Navidrome: native API connection validation failed – %s", exc)
            return False, f"Connection failed: {exc!s}"

    def libraries(self) -> dict[str, str]:
        """Return native Navidrome library IDs and display names."""
        data = self._api_request("GET", "library").json()
        if isinstance(data, dict):
            data = data.get("data", data.get("items", []))
        if not isinstance(data, list):
            raise ValueError("Navidrome native API returned an invalid library list")
        return {str(x["id"]): (x.get("name") or x.get("path") or str(x["id"])) for x in data if isinstance(x, dict) and x.get("id") is not None}

    def scan_libraries(self, url: str | None = None, token: str | None = None) -> dict[str, str]:
        """Scan libraries using Navidrome's native API."""
        if url and token:
            temp_client = NavidromeClient()
            temp_client.url, temp_client.token = url.rstrip("/"), token
            temp_client.username = self.username
            return {name: lib_id for lib_id, name in temp_client.libraries().items()}
        return {name: lib_id for lib_id, name in self.libraries().items()}

    def list_users(self) -> list[User]:
        """Read native Navidrome users and reflect them in Wizarr."""
        server_id = getattr(self, "server_id", None)
        if server_id is None:
            return []
        try:
            remote_users = self._api_request("GET", "user").json()
            if isinstance(remote_users, dict):
                remote_users = remote_users.get("data", remote_users.get("items", []))
            if not isinstance(remote_users, list):
                raise ValueError("Navidrome native API returned an invalid user list")
        except Exception as exc:
            self.remote_errors += 1
            logging.warning("Navidrome: failed to list native API users – %s", exc)
            return []
        by_name = {str(u.get("userName") or u.get("username")): u for u in remote_users if isinstance(u, dict) and (u.get("userName") or u.get("username"))}
        known = User.query.filter(User.server_id == server_id).all()
        if self._skip_prune_on_empty_remote(not by_name, known):
            return known
        try:
            result, rows = [], {}
            for local in known:
                if local.username in by_name:
                    result.append(local)
                    rows.setdefault(local.username, local)
                else:
                    db.session.delete(local)
            for username, remote in by_name.items():
                local = rows.get(username)
                if local is None:
                    local = User(token=str(remote.get("id") or username), username=username, email=remote.get("email") or "", code="empty", server_id=server_id)
                    db.session.add(local)
                    result.append(local)
                else:
                    local.token = str(remote.get("id") or username)
                    local.email = remote.get("email") or local.email
                permissions = StandardizedPermissions.for_navidrome(remote)
                local.allow_downloads, local.allow_live_tv, local.is_admin = permissions.allow_downloads, permissions.allow_live_tv, permissions.is_admin
            db.session.commit()
            return result
        except Exception as exc:
            logging.error("Navidrome: failed to sync native API users – %s", exc)
            db.session.rollback()
            return []

    def create_user(self, username: str, password: str, email: str, *, is_admin: bool = False, allow_downloads: bool = True) -> str:
        """Create an account through Navidrome's native JSON API.

        Navidrome does not expose a per-user download-role flag in its native
        user model, so allow_downloads cannot be enforced by this backend.
        """
        response = self._api_request("POST", "user", {"userName": username, "name": username, "email": email or "", "password": password, "isAdmin": bool(is_admin)})
        data = response.json() if response.content else {}
        return str(data.get("id") or username)

    def update_user(self, username: str, payload: dict[str, Any]):
        """Update a user through Navidrome's native user endpoint."""
        remote = self._find_remote_user(username)
        user_id = remote.get("id")
        if not user_id:
            raise ValueError(f"Navidrome user not found: {username}")
        changes = {}
        if "password" in payload: changes["password"] = payload["password"]
        if "email" in payload: changes["email"] = payload["email"]
        if "is_admin" in payload: changes["isAdmin"] = bool(payload["is_admin"])
        if "name" in payload: changes["name"] = payload["name"]
        if changes:
            self._api_request("PUT", f"user/{user_id}", changes)

    def _find_remote_user(self, identifier: str) -> dict:
        """Find a native Navidrome user by username or server-side ID."""
        users = self._api_request("GET", "user").json()
        if isinstance(users, dict):
            users = users.get("data", users.get("items", []))
        if not isinstance(users, list):
            raise ValueError("Navidrome native API returned an invalid user list")
        for user in users:
            if isinstance(user, dict) and (str(user.get("id", "")) == str(identifier) or str(user.get("userName") or user.get("username") or "") == str(identifier)):
                return user
        raise ValueError(f"Navidrome user not found: {identifier}")

    def enable_user(self, user_id: str) -> bool:  # noqa: ARG002
        """Enable a user account on Navidrome.

        Args:
            user_id: The user's Navidrome ID (unused - Navidrome doesn't support enable/disable)

        Returns:
            bool: True if the user was successfully enabled, False otherwise
        """
        try:
            # Navidrome doesn't have a direct enable feature
            # Return False to indicate this operation is not supported
            structlog.get_logger().warning(
                "Navidrome does not support enabling users. They need to be given library access."
            )
            return False
        except Exception as e:
            structlog.get_logger().error(f"Failed to enable Navidrome user: {e}")
            return False

    def disable_user(self, user_id: str) -> bool:  # noqa: ARG002
        """Disable a user account on Navidrome.

        Args:
            user_id: The user's Navidrome usernameFailed to disable

        Returns:
            bool: True if the user was successfully disabled, False otherwise
        """
        try:
            # Navidrome doesn't have a disable feature, we can only delete users
            # Return False to indicate this operation is not supported
            structlog.get_logger().warning(
                "Navidrome does not support disabling users, only deletion"
            )
            return False
        except Exception as e:
            structlog.get_logger().error(f"Failed to disable Navidrome user: {e}")
            return False

    def delete_user(self, username: str):
        """Delete an account through Navidrome's native JSON API."""
        remote = self._find_remote_user(username)
        user_id = remote.get("id")
        if not user_id:
            raise ValueError(f"Navidrome user not found: {username}")
        self._api_request("DELETE", f"user/{user_id}")

    def get_user(self, username: str):
        """Get user info in legacy format for backward compatibility."""
        details = self.get_user_details(username)
        return {
            "username": details.username,
            "email": details.email,
            "isActive": details.is_enabled,
            "createdAt": int(details.created_at.timestamp() * 1000)
            if details.created_at
            else None,
            "lastSeen": int(details.last_active.timestamp() * 1000)
            if details.last_active
            else None,
            "permissions": {"admin": details.is_admin},
        }

    def get_user_details(self, user_identifier: str | int) -> MediaUserDetails:
        """Return standardized details from Navidrome's native user API."""
        from app.services.media.utils import LibraryAccessHelper, StandardizedPermissions, create_standardized_user_details
        raw = self._find_remote_user(str(user_identifier))
        username = str(raw.get("userName") or raw.get("username") or user_identifier)
        permissions = StandardizedPermissions.for_navidrome(raw)
        created = DateHelper.parse_iso_date(raw.get("createdAt"))
        last_active = DateHelper.parse_iso_date(raw.get("lastAccessAt") or raw.get("lastLoginAt"))
        return create_standardized_user_details(user_id=str(raw.get("id") or username), username=username, email=raw.get("email"), permissions=permissions, library_access=LibraryAccessHelper.create_full_access(), created_at=created, last_active=last_active, is_enabled=True)

    def now_playing(self) -> list[dict]:
        """Navidrome's native API has no supported active-session list."""
        return []

    def statistics(self):
        """Return basic statistics using Navidrome's native API."""
        try:
            users = self._api_request("GET", "user").json()
            if isinstance(users, dict): users = users.get("data", users.get("items", []))
            if not isinstance(users, list): users = []
            return {"library_stats": {}, "user_stats": {"total_users": len(users), "active_sessions": 0}, "server_stats": {"version": "Unknown", "transcoding_sessions": 0}, "content_stats": {}}
        except Exception as exc:
            logging.error("Navidrome statistics: native API request failed – %s", exc)
            return {"library_stats": {}, "user_stats": {"total_users": 0, "active_sessions": 0}, "server_stats": {"version": "Unknown", "transcoding_sessions": 0}, "content_stats": {}, "error": str(exc)}

    def get_user_count(self) -> int:
        """Get lightweight user count from database without triggering sync."""
        try:
            from app.models import MediaServer, User

            if hasattr(self, "server_id") and self.server_id:
                count = User.query.filter_by(server_id=self.server_id).count()
            else:
                # Fallback for legacy settings: find MediaServer for this server type
                servers = MediaServer.query.filter_by(server_type="navidrome").all()
                if servers:
                    server_ids = [s.id for s in servers]
                    count = User.query.filter(User.server_id.in_(server_ids)).count()
                else:
                    # Ultimate fallback: no easy API for user count in Navidrome
                    count = 0
            return count
        except Exception as e:
            logging.error(f"Failed to get Navidrome user count from database: {e}")
            return 0

    def get_server_info(self) -> dict:
        """Get lightweight server information without triggering user sync."""
        try:
            # Navidrome doesn't have traditional sessions/transcoding
            return {
                "version": "Unknown",  # Would need API call to get version
                "transcoding_sessions": 0,  # Navidrome doesn't transcode
                "active_sessions": 0,  # Would need to implement session tracking
            }
        except Exception as e:
            logging.error(f"Failed to get Navidrome server info: {e}")
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
            logging.error(f"Failed to get Navidrome readonly statistics: {e}")
            return {
                "user_stats": {"total_users": 0, "active_sessions": 0},
                "server_stats": {"version": "Unknown", "transcoding_sessions": 0},
                "library_stats": {},
                "content_stats": {},
                "error": str(e),
            }

    def _headers(self) -> dict[str, str]:
        """Return headers for Navidrome's native JSON API."""
        return {"Accept": "application/json", "Content-Type": "application/json"}
