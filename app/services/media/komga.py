import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.media.user_details import MediaUserDetails

import requests
import structlog
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
            headers["X-API-Key"] = self.token
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
                headers = {"X-API-Key": token}
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

    def create_user(
        self, username: str, password: str, email: str, allow_downloads: bool = False
    ) -> str:
        """Create a new Komga user and return the user ID.

        Args:
            username: Username for the new user (not used by Komga, only email)
            password: Password for the new user
            email: Email address for the new user
            allow_downloads: Whether to grant FILE_DOWNLOAD role

        Returns:
            str: The new user's ID
        """
        roles = ["USER"]
        if allow_downloads:
            roles.append("FILE_DOWNLOAD")

        payload = {"email": email, "password": password, "roles": roles}
        response = self.post("/api/v2/users", json=payload)
        return response.json()["id"]

    def update_user(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update a Komga user."""
        response = self.patch(f"/api/v2/users/{user_id}", json=updates)
        return response.json()

    def enable_user(self, user_id: str) -> bool:
        """Enable a user account on Komga.

        Args:
            user_id: The user's Komga ID

        Returns:
            bool: True if the user was successfully enabled, False otherwise
        """
        try:
            # Komga doesn't have a direct enable feature
            # Return False to indicate this operation is not supported
            structlog.get_logger().warning("Komga does not support enabling users. They need to be given library access.")
            return False
        except Exception as e:
            structlog.get_logger().error(f"Failed to enable Komga user: {e}")
            return False

    def disable_user(self, user_id: str, enable: bool = False) -> bool:
        """Disable a user account on Komga.

        Args:
            user_id: The user's Komga ID
            enable: If True, enables the user (sets IsDisabled=False). 
                If False (default), disables the user (sets IsDisabled=True).

        Returns:
            bool: True if the user was successfully disabled, False otherwise
        """
        try:
            if enable is True:
                return enable_user(self, user_id) # Enable not supported
            # Komga doesn't have a direct disable feature
            # We can remove all library access to effectively disable the user
            user_data = {"sharedLibrariesIds": []}
            response = self.patch(f"/api/v2/users/{user_id}", json=user_data)
            return response.status_code == 204 or response.status_code == 200
        except Exception as e:
            action = "enable" if enable else "disable"
            structlog.get_logger().error(f"Failed to {action} Komga user: {e}")
            return False

    def delete_user(self, user_id: str) -> None:
        """Delete a Komga user."""
        self.delete(f"/api/v2/users/{user_id}")

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
        response = self.get(f"/api/v2/users/{user_id}")
        raw_user = response.json()

        # Extract permissions using utility
        roles = raw_user.get("roles", [])
        permissions = StandardizedPermissions.for_basic_server(
            "komga",
            is_admin="ADMIN" in roles,
            allow_downloads="FILE_DOWNLOAD" in roles,
        )

        # Handle library access - always return actual library names

        if raw_user.get("sharedAllLibraries", False):
            # User has access to all libraries - fetch all library IDs from server
            all_libraries = self.libraries()  # Returns {id: name} mapping
            shared_library_ids = list(all_libraries.keys())
        else:
            # User has restricted library access
            shared_library_ids = raw_user.get("sharedLibrariesIds", [])

        # Always create restricted access with the actual library IDs
        library_access = (
            LibraryAccessHelper.create_restricted_access(
                shared_library_ids, getattr(self, "server_id", None)
            )
            if shared_library_ids
            else []
        )

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
            response = self.get("/api/v2/users")
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

            # Add policy attributes including library access from Komga
            for user in users:
                # Get the full user data from Komga to extract library info
                komga_user_data = komga_users.get(user.token, {})
                roles = komga_user_data.get("roles", [])

                # Check for FILE_DOWNLOAD role to determine download permission
                allow_downloads = "FILE_DOWNLOAD" in roles

                # Store both server-specific and standardized keys in policies dict
                komga_policies = {
                    # Server-specific data (Komga user info)
                    "enabled": True,  # Komga users are enabled by default
                    "sharedAllLibraries": komga_user_data.get(
                        "sharedAllLibraries", False
                    ),
                    "sharedLibrariesIds": komga_user_data.get("sharedLibrariesIds", []),
                    "roles": roles,
                    # Standardized permission keys for UI display
                    "allow_downloads": allow_downloads,
                    "allow_live_tv": False,  # Komga doesn't have Live TV
                    "allow_sync": True,  # Default to True for reading apps
                }
                user.set_raw_policies(komga_policies)

                # Update standardized User model columns
                user.allow_downloads = allow_downloads
                user.allow_live_tv = False  # Komga doesn't have Live TV
                user.is_admin = "ADMIN" in roles

            # Single commit for all metadata updates
            try:
                db.session.commit()
            except Exception as e:
                logging.error("Komga: failed to update user metadata – %s", e)
                db.session.rollback()
                return []

            # Cache detailed metadata for all users (including library access)
            self._cache_user_metadata_from_bulk_response(users, komga_users)

            # Commit the standardized metadata updates
            try:
                db.session.commit()
            except Exception as e:
                logging.error(
                    f"Komga: failed to commit standardized metadata updates: {e}"
                )
                db.session.rollback()

            return users
        except Exception as e:
            logging.error(f"Failed to list Komga users: {e}")
            return []

    def _cache_user_metadata_from_bulk_response(
        self, users: list[User], komga_users: dict
    ) -> None:
        """Cache user metadata from bulk API response without individual API calls.

        Args:
            users: List of User objects to cache metadata for
            komga_users: Dictionary of raw user data from bulk /api/v2/users response
        """
        if not users or not komga_users:
            return

        from app.services.media.utils import (
            DateHelper,
            LibraryAccessHelper,
            StandardizedPermissions,
            create_standardized_user_details,
        )

        cached_count = 0
        for user in users:
            try:
                # Get the raw user data from bulk response
                raw_user = komga_users.get(user.token)
                if not raw_user:
                    continue

                roles = raw_user.get("roles", [])

                # Extract standardized permissions
                permissions = StandardizedPermissions.for_basic_server(
                    "komga",
                    is_admin="ADMIN" in roles,
                    allow_downloads="FILE_DOWNLOAD" in roles,
                )

                # Handle library access - always return actual library names
                if raw_user.get("sharedAllLibraries", False):
                    # User has access to all libraries - fetch all library IDs from server
                    all_libraries = self.libraries()  # Returns {id: name} mapping
                    shared_library_ids = list(all_libraries.keys())
                else:
                    # User has restricted library access
                    shared_library_ids = raw_user.get("sharedLibrariesIds", [])

                # Always create restricted access with the actual library IDs
                library_access = (
                    LibraryAccessHelper.create_restricted_access(
                        shared_library_ids, getattr(self, "server_id", None)
                    )
                    if shared_library_ids
                    else []
                )

                # Parse dates
                created_at = DateHelper.parse_iso_date(raw_user.get("createdDate"))
                last_active = DateHelper.parse_iso_date(raw_user.get("lastActiveDate"))

                # Create standardized user details
                details = create_standardized_user_details(
                    user_id=user.token,
                    username=raw_user.get("email", "Unknown"),
                    email=raw_user.get("email"),
                    permissions=permissions,
                    library_access=library_access,
                    raw_policies=raw_user,
                    created_at=created_at,
                    last_active=last_active,
                    is_enabled=True,  # Komga doesn't have a disabled state
                )

                # Update the standardized metadata columns in the User record
                user.update_standardized_metadata(details)
                cached_count += 1

            except Exception as e:
                logging.warning(
                    f"Failed to cache metadata for Komga user {user.token}: {e}"
                )
                continue

        if cached_count > 0:
            logging.info(f"Cached metadata for {cached_count} Komga users")

    def _set_library_access(self, user_id: str, library_ids: list[str]) -> None:
        """Set library access for a user."""
        if not library_ids:
            return

        try:
            # Use v2 API to set library access via user update
            updates = {"sharedLibraries": {"all": False, "libraryIds": library_ids}}
            self.patch(f"/api/v2/users/{user_id}", json=updates)
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
            inv = Invitation.query.filter_by(code=code).first()
            current_server_id = getattr(self, "server_id", None)

            # Get download permission from invitation, or fall back to server default
            if inv and inv.allow_downloads is not None:
                allow_downloads = inv.allow_downloads
            else:
                # Use server's default download policy
                from app.models import MediaServer

                server = (
                    MediaServer.query.get(current_server_id)
                    if current_server_id
                    else None
                )
                allow_downloads = server.allow_downloads if server else False

            user_id = self.create_user(
                username, password, email, allow_downloads=allow_downloads
            )

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
                users_response = self.get("/api/v2/users").json()
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
                        users = self.get("/api/v2/users").json()
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

    def get_recent_items(self, limit: int = 6) -> list[dict[str, str]]:
        """Get recently added books from Komga for the wizard widget.

        Args:
            limit: Maximum number of items to return

        Returns:
            list: List of dicts with 'title' and 'thumb' keys
        """
        try:
            # Get latest books from Komga API
            response = self.get(f"/api/v1/books/latest?size={limit}")
            books = response.json().get("content", [])

            items = []
            for book in books:
                # Get book ID for thumbnail
                book_id = book.get("id")

                if book_id:
                    # Construct thumbnail URL with authentication
                    thumb_url = (
                        f"{self.url.rstrip('/')}/api/v1/books/{book_id}/thumbnail"
                    )

                    # Generate secure proxy URL with opaque token
                    thumb_url = self.generate_image_proxy_url(thumb_url)

                    items.append(
                        {
                            "title": book.get("metadata", {}).get("title")
                            or book.get("name", "Unknown"),
                            "thumb": thumb_url,
                        }
                    )

            return items

        except Exception as e:
            logging.warning(f"Failed to get recent items from Komga: {e}")
            return []
