from __future__ import annotations

import hashlib
import logging
import random
import string
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import requests
import structlog
from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, User
from app.services.invites import is_invite_valid
from app.services.media.utils import StandardizedPermissions

from .client_base import RestApiMixin, register_media_client

if TYPE_CHECKING:
    from app.services.media.user_details import MediaUserDetails


@register_media_client("navidrome")
class NavidromeClient(RestApiMixin):
    """Navidrome wrapper.

    Read-only data (ping, libraries, now playing, cover art) uses the
    Subsonic API. User management uses Navidrome's native REST API, because
    the Subsonic ``createUser``/``updateUser``/``deleteUser`` endpoints
    answer 501 Not Implemented and ``getUsers`` only returns the logged-in
    user.
    """

    @classmethod
    def check_connection(cls, url: str, token: str) -> tuple[bool, str]:
        from app.services.servers import check_navidrome

        return check_navidrome(url, token)

    #: API prefix for Subsonic/OpenSubsonic endpoints
    API_PREFIX = "/rest"

    #: API prefix for Navidrome's native REST endpoints
    NATIVE_API_PREFIX = "/api"

    #: Username used for admin API access. The Subsonic layer has always
    #: hardcoded ``u=admin`` with the configured API key as its password, so
    #: the native login keeps the same semantics.
    ADMIN_USERNAME = "admin"

    def __init__(self, *args, **kwargs):
        # Provide defaults for legacy compatibility
        kwargs.setdefault("url_key", "server_url")
        kwargs.setdefault("token_key", "api_key")

        super().__init__(*args, **kwargs)

        # Cached native-API bearer token (JWT from /auth/login)
        self._native_token: str | None = None

        # Normalize URL
        if self.url:
            self.url = self.url.rstrip("/")

    def _generate_auth_params(self) -> dict[str, str]:
        """Generate authentication parameters for Subsonic API calls.

        Uses the recommended salted hash method for security.
        """
        if not self.token:
            raise ValueError("API token (password) is required for Navidrome")

        # Generate random salt
        salt = "".join(random.choices(string.ascii_letters + string.digits, k=6))

        # Create MD5 hash of password + salt
        token_hash = hashlib.md5((self.token + salt).encode()).hexdigest()  # noqa: S324  # Required by Subsonic API specification

        return {
            "u": "admin",  # Default username for API access
            "t": token_hash,
            "s": salt,
            "v": "1.16.1",  # Supported API version
            "c": "wizarr",  # Client identifier
            "f": "json",  # Response format
        }

    def _subsonic_request(self, endpoint: str, params: dict | None = None) -> dict:
        """Make a request to the Subsonic API with proper authentication."""
        auth_params = self._generate_auth_params()
        if params:
            auth_params.update(params)

        response = self.get(f"{self.API_PREFIX}/{endpoint}", params=auth_params)
        response.raise_for_status()

        data = response.json()

        # Check for Subsonic API errors
        subsonic_response = data.get("subsonic-response", {})
        if subsonic_response.get("status") != "ok":
            error = subsonic_response.get("error", {})
            raise Exception(
                f"Subsonic API error: {error.get('message', 'Unknown error')}"
            )

        return subsonic_response

    # ------------------------------------------------------------------
    # Native API (user management)
    # ------------------------------------------------------------------

    def _native_login(self) -> str:
        """Log in to the native API and return a bearer token (JWT)."""
        if not self.token:
            raise ValueError("API token (password) is required for Navidrome")

        response = self.post(
            "/auth/login",
            json={"username": self.ADMIN_USERNAME, "password": self.token},
            headers={"Content-Type": "application/json"},
        )
        token = response.json().get("token")
        if not isinstance(token, str) or not token:
            raise ValueError("Navidrome login did not return a token")
        self._native_token = token
        return token

    def _native_request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
    ) -> Any:
        """Call a native API endpoint, re-authenticating once on 401."""
        for attempt in range(2):
            token = getattr(self, "_native_token", None) or self._native_login()
            headers = {
                "x-nd-authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            try:
                response = self._request(
                    method,
                    f"{self.NATIVE_API_PREFIX}{path}",
                    json=json,
                    headers=headers,
                )
            except requests.HTTPError as exc:
                status = getattr(exc.response, "status_code", None)
                if status == 401 and attempt == 0:
                    # Cached JWT expired – log in again, retry exactly once.
                    self._native_token = None
                    continue
                raise
            try:
                return response.json()
            except ValueError:
                return None
        raise RuntimeError(
            "Navidrome native API retry loop exhausted"
        )  # pragma: no cover

    def _native_users(self) -> list[dict]:
        """Return all users from the native API.

        Every entry must be a dict with a nonempty string ``id`` and
        ``userName``. A snapshot containing malformed entries raises instead
        of being silently filtered, so a broken remote response can never
        partially prune local rows.
        """
        users = self._native_request("GET", "/user")
        if not isinstance(users, list):
            raise ValueError("Navidrome returned an invalid user list")
        for user in users:
            if not (
                isinstance(user, dict)
                and isinstance(user.get("id"), str)
                and user["id"]
                and isinstance(user.get("userName"), str)
                and user["userName"]
            ):
                raise ValueError("Navidrome returned an invalid user list")
        return users

    @staticmethod
    def _path_segment(identifier: Any) -> str:
        """Quote a user id/username as exactly one URL path segment."""
        return quote(str(identifier), safe="")

    def _resolve_native_user(self, identifier: str) -> dict:
        """Fetch a user by native id, falling back to a username lookup.

        Older Wizarr versions stored the Navidrome username in ``User.token``,
        so identifiers may be either a native id or a username. Raises the
        original 404 ``HTTPError`` when neither matches, so callers can treat
        the user as already gone.
        """
        try:
            user = self._native_request(
                "GET", f"/user/{self._path_segment(identifier)}"
            )
            if isinstance(user, dict) and user.get("id"):
                return user
            raise ValueError(f"Navidrome returned an invalid user for {identifier!r}")
        except requests.HTTPError as exc:
            if getattr(exc.response, "status_code", None) != 404:
                raise
            for user in self._native_users():
                if user.get("userName") == identifier:
                    return user
            raise

    @staticmethod
    def _reject_download_restriction() -> None:
        """Navidrome has no per-user download role – reject, don't pretend.

        Raised before any network mutation: provisioning a user while
        silently ignoring an explicitly configured download restriction
        would weaken the configured policy.
        """
        raise ValueError(
            "Navidrome cannot enforce a per-user download restriction "
            "(downloads follow the server-wide EnableDownloads setting); "
            "refusing to provision the user with downloads disabled."
        )

    @staticmethod
    def _parse_native_dt(value: Any) -> datetime | None:
        """Parse an RFC 3339 timestamp from the native API, or return None."""
        if not value or not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def validate_connection(self) -> tuple[bool, str]:
        """Validate connection to Navidrome server."""
        try:
            # Test connection with ping endpoint
            result = self._subsonic_request("ping")
            if result.get("status") == "ok":
                return True, "Connection successful"
            return False, "Server did not respond properly"
        except Exception as exc:
            logging.error("Navidrome: connection validation failed – %s", exc)
            return False, f"Connection failed: {exc!s}"

    def libraries(self) -> dict[str, str]:
        """Return mapping of library_id → display_name."""
        try:
            result = self._subsonic_request("getMusicFolders")
            folders = result.get("musicFolders", {}).get("musicFolder", [])

            # Handle single folder response (not in array)
            if isinstance(folders, dict):
                folders = [folders]

            return {str(folder["id"]): folder["name"] for folder in folders}
        except Exception as exc:
            logging.warning("Navidrome: failed to fetch libraries – %s", exc)
            return {}

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        """Scan available libraries on this Navidrome server."""
        try:
            if url and token:
                # Create temporary client for scanning
                temp_client = NavidromeClient()
                temp_client.url = url.rstrip("/")
                temp_client.token = token
                return {
                    name: lib_id for lib_id, name in temp_client.libraries().items()
                }
            # Use saved credentials
            return {name: lib_id for lib_id, name in self.libraries().items()}
        except Exception as exc:
            logging.warning("Navidrome: failed to scan libraries – %s", exc)
            return {}

    def list_users(self) -> list[User]:
        """Read users from Navidrome's native API and reflect them locally."""
        server_id = getattr(self, "server_id", None)
        if server_id is None:
            return []

        try:
            users_data = self._native_users()
        except Exception as exc:
            logging.warning("Navidrome: failed to list users – %s", exc)
            return []

        users_by_name = {u["userName"]: u for u in users_data}

        known_users = User.query.filter(User.server_id == server_id).all()
        if self._skip_prune_on_empty_remote(not users_by_name, known_users):
            return known_users

        try:
            # Use the rows that are already loaded, not one query for each
            # remote user. The first local row with a username is the match.
            users: list[User] = []
            rows_by_username: dict[str, User] = {}
            for local in known_users:
                if local.username in users_by_name:
                    users.append(local)
                    rows_by_username.setdefault(local.username, local)
                else:
                    # Remove users that no longer exist upstream
                    db.session.delete(local)

            # Add new users or update existing ones
            for username, remote in users_by_name.items():
                db_row = rows_by_username.get(username)
                if db_row is None:
                    db_row = User(
                        token=remote.get("id", username),
                        username=username,
                        email=remote.get("email", ""),
                        code="empty",
                        server_id=server_id,
                    )
                    db.session.add(db_row)
                    users.append(db_row)
                else:
                    db_row.email = remote.get("email", db_row.email)
                    # Migrate legacy rows that stored the username as token
                    if remote.get("id"):
                        db_row.token = remote["id"]

            # Enhance users with policy data from Navidrome
            for user in users:
                # Use standardized permissions helper for consistency
                permissions = StandardizedPermissions.for_navidrome(
                    users_by_name[user.username]
                )

                # Update standardized User model columns
                user.allow_downloads = permissions.allow_downloads
                user.allow_live_tv = permissions.allow_live_tv
                user.is_admin = permissions.is_admin

            # Single commit for all user and metadata updates
            db.session.commit()

        except Exception as exc:
            logging.error("Navidrome: failed to sync users – %s", exc)
            db.session.rollback()
            return []
        return users

    def create_user(
        self,
        username: str,
        password: str,
        email: str,
        *,
        is_admin: bool = False,
        allow_downloads: bool = True,
    ) -> str:
        """Create a user via the native API and return the native user id."""
        if not allow_downloads:
            self._reject_download_restriction()
        try:
            payload = {
                "userName": username,
                "name": username,
                "email": email,
                "password": password,
                "isAdmin": is_admin,
            }
            created = self._native_request("POST", "/user", json=payload)
            user_id = created.get("id") if isinstance(created, dict) else None
            if not user_id:
                # Older/newer builds may answer with a different body shape;
                # confirm the user really exists before claiming success.
                user_id = self._resolve_native_user(username)["id"]
            return user_id
        except Exception as exc:
            logging.error("Navidrome: failed to create user – %s", exc)
            raise

    def update_user(self, user_identifier: str, payload: dict[str, Any]):
        """Update a user via the native API.

        ``user_identifier`` may be the native id or (legacy) the username.
        Navidrome's PUT replaces the record, so the current user is fetched
        and merged first.
        """
        if "allow_downloads" in payload and not payload["allow_downloads"]:
            self._reject_download_restriction()
        try:
            current = self._resolve_native_user(user_identifier)
            # Shallow copy preserves every fetched field (scrobbleFilter,
            # libraries, timestamps, future additions) since PUT replaces
            # the record. Never replay secrets from the fetched object.
            body = dict(current)
            body.pop("password", None)
            body.pop("currentPassword", None)
            if "email" in payload:
                body["email"] = payload["email"]
            if "is_admin" in payload:
                body["isAdmin"] = bool(payload["is_admin"])
            if payload.get("password"):
                body["password"] = payload["password"]

            self._native_request(
                "PUT", f"/user/{self._path_segment(current['id'])}", json=body
            )
        except Exception as exc:
            logging.error(
                "Navidrome: failed to update user %s – %s", user_identifier, exc
            )
            raise

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

    def delete_user(self, user_identifier: str):
        """Delete a user via the native API.

        ``user_identifier`` may be the native id or (legacy) the username.
        A user the server no longer knows raises the underlying 404 so the
        caller can treat it as already deleted.
        """
        try:
            user = self._resolve_native_user(user_identifier)
            self._native_request("DELETE", f"/user/{self._path_segment(user['id'])}")
        except Exception as exc:
            logging.error(
                "Navidrome: failed to delete user %s – %s", user_identifier, exc
            )
            raise

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
        """Get detailed user information in standardized format."""
        from app.services.media.utils import (
            LibraryAccessHelper,
            StandardizedPermissions,
            create_standardized_user_details,
        )

        # Accepts a native id or (legacy) a username
        raw_user = self._resolve_native_user(str(user_identifier))

        # Extract standardized permissions using shared utility
        permissions = StandardizedPermissions.for_navidrome(raw_user)

        # Navidrome gives full access to all libraries
        library_access = LibraryAccessHelper.create_full_access()

        last_active = self._parse_native_dt(
            raw_user.get("lastAccessAt") or raw_user.get("lastLoginAt")
        )

        return create_standardized_user_details(
            user_id=raw_user["id"],
            username=raw_user.get("userName", str(user_identifier)),
            email=raw_user.get("email"),
            permissions=permissions,
            library_access=library_access,
            created_at=self._parse_native_dt(raw_user.get("createdAt")),
            last_active=last_active,
            is_enabled=True,  # Navidrome doesn't have disabled users concept
        )

    def _do_join(
        self,
        username: str,
        password: str,
        confirm: str,
        email: str,
        code: str,
    ):
        """Public invite flow for Navidrome users."""
        if not 1 <= len(username) <= 50:
            return False, "Username must be 1-50 characters."
        if not 8 <= len(password) <= 128:
            return False, "Password must be 8-128 characters."
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

            # Get download permission from invitation
            allow_downloads = getattr(inv, "allow_downloads", True)
            if allow_downloads is None:
                allow_downloads = True

            # Create user on Navidrome
            user_id = self.create_user(
                username, password, email=email, allow_downloads=allow_downloads
            )
            if not user_id:
                return False, "Failed to create user on server"

            # Calculate expiry
            from app.services.expiry import calculate_user_expiry

            expires = (
                calculate_user_expiry(inv, getattr(self, "server_id", None))
                if inv
                else None
            )

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

            return True, ""

        except ValueError as exc:
            # e.g. an invite requesting an unenforceable download restriction
            logging.error("Navidrome join rejected: %s", exc)
            db.session.rollback()
            return False, str(exc)
        except Exception as exc:
            logging.error("Navidrome join failed: %s", exc)
            db.session.rollback()
            return False, "Failed to create user"

    def now_playing(self) -> list[dict]:
        """Return active sessions from Navidrome.

        Raises when the session list cannot be fetched or read. Then a caller
        can tell a failed poll from a server with no sessions. Returns [] only
        when the server reports no sessions.
        """
        result = self._subsonic_request("getNowPlaying")
        now_playing_data = result.get("nowPlaying") or {}
        if not isinstance(now_playing_data, dict):
            raise ValueError("Navidrome returned an invalid now playing list")
        entries = now_playing_data.get("entry", [])

        # Handle single entry response (not in array)
        if isinstance(entries, dict):
            entries = [entries]
        if not isinstance(entries, list):
            raise ValueError("Navidrome returned an invalid now playing list")

        active = []
        for entry in entries:
            try:
                session_data = self._now_playing_entry(entry)
            except Exception as exc:
                # One bad entry must not hide the other sessions.
                logging.warning("Navidrome: failed to read a session – %s", exc)
                continue
            active.append(session_data)

        return active

    def _now_playing_entry(self, entry: dict) -> dict:
        """Convert one getNowPlaying entry to a now-playing dict."""
        session_data = {
            "user_name": entry.get("username", "Unknown"),
            "media_title": entry.get("title", "Unknown Track"),
            "media_type": "track",
            "progress": 0.0,  # Navidrome doesn't provide progress in now playing
            "state": "playing",
            "session_id": entry.get("id", ""),
            "client": entry.get("playerName", "Unknown"),
            "device_name": entry.get("playerName", "Unknown Device"),
            "position_ms": 0,
            "duration_ms": (entry.get("duration", 0) * 1000)
            if entry.get("duration")
            else 0,
            "artwork_url": f"{self.url}{self.API_PREFIX}/getCoverArt?id={entry.get('coverArt', '')}&"
            + "&".join(f"{k}={v}" for k, v in self._generate_auth_params().items())
            if entry.get("coverArt")
            else None,
            "thumbnail_url": None,
            "transcoding": {"is_transcoding": False, "direct_play": True},
        }

        # Add artist and album info if available
        if entry.get("artist"):
            session_data["artist"] = entry["artist"]
        if entry.get("album"):
            session_data["album"] = entry["album"]

        return session_data

    def statistics(self):
        """Return server statistics for Navidrome."""
        try:
            stats = {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
            }

            # Get user count
            try:
                total_users = len(self._native_users())
            except Exception as exc:
                logging.error("Navidrome statistics: failed to fetch users – %s", exc)
                total_users = 0

            # Get active sessions
            try:
                active_sessions = self.now_playing()
            except Exception as exc:
                logging.error(
                    "Navidrome statistics: failed to calculate active sessions – %s",
                    exc,
                )
                active_sessions = []

            stats["user_stats"] = {
                "total_users": total_users,
                "active_sessions": len(active_sessions),
            }

            stats["server_stats"] = {
                "version": "Unknown",  # Navidrome doesn't expose version in Subsonic API
                "transcoding_sessions": 0,  # Not applicable for music streaming
            }

            return stats

        except Exception as e:
            logging.error(f"Failed to get Navidrome statistics: {e}")
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
        """Return default headers for requests."""
        return {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
