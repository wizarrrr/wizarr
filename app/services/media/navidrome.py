from __future__ import annotations

import hashlib
import logging
import random
import string
from typing import TYPE_CHECKING, Any

from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, Library, User
from app.services.invites import is_invite_valid

from .client_base import RestApiMixin, register_media_client

if TYPE_CHECKING:
    from app.services.media.user_details import MediaUserDetails


@register_media_client("navidrome")
class NavidromeClient(RestApiMixin):
    """Navidrome wrapper using the Subsonic API."""

    #: API prefix for Subsonic/OpenSubsonic endpoints
    API_PREFIX = "/rest"

    def __init__(self, *args, **kwargs):
        # Provide defaults for legacy compatibility
        kwargs.setdefault("url_key", "server_url")
        kwargs.setdefault("token_key", "api_key")

        super().__init__(*args, **kwargs)

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
        token_hash = hashlib.md5((self.token + salt).encode()).hexdigest()

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
            return False, f"Connection failed: {str(exc)}"

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
        """Read users from Navidrome and reflect them locally."""
        server_id = getattr(self, "server_id", None)
        if server_id is None:
            return []

        try:
            result = self._subsonic_request("getUsers")
            users_data = result.get("users", {}).get("user", [])

            # Handle single user response (not in array)
            if isinstance(users_data, dict):
                users_data = [users_data]
        except Exception as exc:
            logging.warning("Navidrome: failed to list users – %s", exc)
            return []

        users_by_name = {u["username"]: u for u in users_data}

        try:
            # Add new users or update existing ones
            for username, remote in users_by_name.items():
                db_row = User.query.filter_by(
                    username=username, server_id=server_id
                ).first()
                if not db_row:
                    db_row = User(
                        token=username,  # Use username as token for Navidrome
                        username=username,
                        email=remote.get("email", ""),
                        code="empty",
                        server_id=server_id,
                    )
                    db.session.add(db_row)
                else:
                    db_row.email = remote.get("email", db_row.email)

            # Remove users that no longer exist upstream
            to_check = User.query.filter(User.server_id == server_id).all()
            for local in to_check:
                if local.username not in users_by_name:
                    db.session.delete(local)

            db.session.commit()

        except Exception as exc:
            logging.error("Navidrome: failed to sync users – %s", exc)
            db.session.rollback()
            return []

        # Get users with policy information
        users = User.query.filter(User.server_id == server_id).all()

        # Enhance users with policy data from Navidrome
        for user in users:
            if user.username in users_by_name:
                # Navidrome users can always download/sync music
                user.allow_downloads = True
                user.allow_sync = True
                # No live TV in music servers
                user.allow_live_tv = False
            else:
                # Default values if user data not found
                user.allow_downloads = False
                user.allow_live_tv = False
                user.allow_sync = False

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
        """Create a user and return the username (Navidrome uses username as identifier)."""
        try:
            params = {
                "username": username,
                "password": password,
                "email": email,
                "adminRole": "true" if is_admin else "false",
                "downloadRole": "true" if allow_downloads else "false",
                "uploadRole": "false",  # Don't allow uploads by default
                "playlistRole": "true",  # Allow playlist creation
                "coverArtRole": "false",  # Don't allow cover art changes
                "commentRole": "false",  # Don't allow comments
                "podcastRole": "false",  # Don't allow podcast management
                "streamRole": "true",  # Allow streaming
                "jukeboxRole": "false",  # Don't allow jukebox mode
                "shareRole": "false",  # Don't allow sharing
            }

            self._subsonic_request("createUser", params)
            return username
        except Exception as exc:
            logging.error("Navidrome: failed to create user – %s", exc)
            raise

    def update_user(self, username: str, payload: dict[str, Any]):
        """Update user with given parameters."""
        try:
            params = {"username": username}

            # Map common payload fields to Subsonic parameters
            if "password" in payload:
                params["password"] = payload["password"]
            if "email" in payload:
                params["email"] = payload["email"]
            if "is_admin" in payload:
                params["adminRole"] = "true" if payload["is_admin"] else "false"
            if "allow_downloads" in payload:
                params["downloadRole"] = (
                    "true" if payload["allow_downloads"] else "false"
                )

            self._subsonic_request("updateUser", params)
        except Exception as exc:
            logging.error("Navidrome: failed to update user %s – %s", username, exc)
            raise

    def delete_user(self, username: str):
        """Delete a user permanently from Navidrome."""
        try:
            self._subsonic_request("deleteUser", {"username": username})
        except Exception as exc:
            logging.error("Navidrome: failed to delete user %s – %s", username, exc)
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

    def get_user_details(self, username: str) -> MediaUserDetails:
        """Get detailed user information in standardized format."""
        from app.services.media.user_details import MediaUserDetails, UserLibraryAccess

        # Get raw user data from Navidrome API
        result = self._subsonic_request("getUser", {"username": username})
        raw_user = result.get("user", {})

        # All users have access to all libraries in Navidrome
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

        # Extract policies information
        filtered_policies = {
            "adminRole": raw_user.get("adminRole", False),
            "downloadRole": raw_user.get("downloadRole", True),
            "uploadRole": raw_user.get("uploadRole", False),
            "playlistRole": raw_user.get("playlistRole", True),
            "streamRole": raw_user.get("streamRole", True),
        }

        return MediaUserDetails(
            user_id=username,
            username=raw_user.get("username", username),
            email=raw_user.get("email"),
            is_admin=raw_user.get("adminRole", False),
            is_enabled=True,  # Navidrome doesn't have disabled users concept
            created_at=None,  # Navidrome doesn't expose creation date
            last_active=None,  # Navidrome doesn't expose last seen
            library_access=library_access,
            raw_policies=filtered_policies,
        )

    def _do_join(
        self, username: str, password: str, confirm: str, email: str, code: str
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

        except Exception as exc:
            logging.error("Navidrome join failed: %s", exc)
            db.session.rollback()
            return False, "Failed to create user"

    def now_playing(self) -> list[dict]:
        """Return active sessions from Navidrome."""
        try:
            result = self._subsonic_request("getNowPlaying")
            entries = result.get("nowPlaying", {}).get("entry", [])

            # Handle single entry response (not in array)
            if isinstance(entries, dict):
                entries = [entries]

            active = []
            for entry in entries:
                # Extract session information
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
                    + "&".join(
                        f"{k}={v}" for k, v in self._generate_auth_params().items()
                    )
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

                active.append(session_data)

            return active
        except Exception as exc:
            logging.error("Navidrome: failed to fetch now playing – %s", exc)
            return []

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
                result = self._subsonic_request("getUsers")
                users_data = result.get("users", {}).get("user", [])
                if isinstance(users_data, dict):
                    users_data = [users_data]
                total_users = len(users_data)
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

    def _headers(self) -> dict[str, str]:
        """Return default headers for requests."""
        return {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
