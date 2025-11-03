import logging
import re
import threading
from typing import TYPE_CHECKING, Any

import structlog
from cachetools import TTLCache, cached
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer

from app.extensions import db
from app.models import Invitation, Library, MediaServer, User
from app.services.media.service import get_client_for_media_server
from app.services.notifications import notify

from .client_base import MediaClient, register_media_client
from .plex_custom import accept_invite_v2, update_shared_server

if TYPE_CHECKING:
    from app.services.media.user_details import MediaUserDetails


# Patch PlexAPI's acceptInvite method with our custom v2 implementation
MyPlexAccount.acceptInvite = accept_invite_v2  # type: ignore[assignment]


def extract_plex_error_message(exception) -> str:
    """
    Extract human-readable error message from Plex API exceptions.

    Args:
        exception: Exception from plexapi

    Returns:
        Human-readable error message
    """
    error_message = str(exception)

    # Look for XML response with status attribute in the error message
    # Format: plexapi.exceptions.BadRequest: (400) bad_request; https://... <Response code="400" status="Error message"/>
    xml_pattern = r'<Response[^>]+status="([^"]*)"[^>]*/?>'
    xml_match = re.search(xml_pattern, error_message)
    if xml_match:
        return xml_match.group(1)

    # Look for JSON response patterns if XML doesn't work
    # This handles cases where Plex returns JSON errors
    json_pattern = r'"message":\s*"([^"]*)"'
    json_match = re.search(json_pattern, error_message)
    if json_match:
        return json_match.group(1)

    # Look for simple status messages in parentheses
    # Format: (400) some_error_message; ...
    status_pattern = r"\(\d+\)\s+([^;]+);"
    status_match = re.search(status_pattern, error_message)
    if status_match:
        error_text = status_match.group(1).strip()
        # Convert snake_case to readable text
        return error_text.replace("_", " ").title()

    # Fallback to the original exception message but clean it up
    if hasattr(exception, "message"):
        return str(exception.message)

    # Last resort: return a cleaned up version of the exception string
    clean_message = (
        error_message.split(";")[0] if ";" in error_message else error_message
    )
    return clean_message.replace("plexapi.exceptions.", "").replace("BadRequest: ", "")


class PlexInvitationError(Exception):
    """Custom exception for Plex invitation errors with user-friendly messages."""

    def __init__(self, message: str, original_exception=None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(message)


@register_media_client("plex")
class PlexClient(MediaClient):
    """Wrapper that connects to Plex using admin credentials."""

    def __init__(self, *args, **kwargs):
        if "url_key" not in kwargs:
            kwargs["url_key"] = "server_url"
        if "token_key" not in kwargs:
            kwargs["token_key"] = "api_key"  # noqa: S105  # Parameter name, not actual password

        super().__init__(*args, **kwargs)
        self._server = None
        self._admin = None

    @property
    def server(self) -> PlexServer:
        if self._server is None:
            self._server = PlexServer(self.url, self.token)
        return self._server

    @property
    def admin(self) -> MyPlexAccount:
        if self._admin is None:
            try:
                self._admin = MyPlexAccount(token=self.token)
            except Exception as e:
                logging.error(f"Failed to connect to Plex MyPlexAccount: {e}")
                # Instead of raising, return None and let callers handle it
                raise ConnectionError(f"Unable to connect to Plex servers: {e}") from e
        return self._admin

    def libraries(self) -> dict[str, str]:
        """Get all libraries with their global IDs.

        Returns:
            dict: Mapping of {global_id: library_name} for database storage
                  where global_id is used as external_id in the Library model
        """
        # Get global library IDs from Plex API
        library_map = self._get_all_library_global_ids()

        # Return {global_id: name} so external_id stores the global ID
        return {str(global_id): name for name, global_id in library_map.items()}

    # ─── Helper Methods ────────────────────────────────────────────────────────

    def _get_server_users(self) -> list[User]:
        """Get all users for this server from database."""
        return db.session.query(User).filter(User.server_id == self.server_id).all()

    def _extract_plex_permissions(self, plex_user) -> dict[str, bool]:
        """Extract all permissions from a Plex user object."""
        return {
            "is_admin": getattr(plex_user, "admin", False),
            "allow_downloads": getattr(plex_user, "allowSync", False),
            "allow_live_tv": getattr(plex_user, "allowChannels", False),
            "allow_camera_upload": getattr(plex_user, "allowCameraUpload", False),
        }

    def _filter_users_for_server(self, admin_users, server_id: str) -> dict[str, Any]:
        """Filter Plex users who have access to this specific server."""
        users_by_email = {}
        for plex_user in admin_users:
            email = getattr(plex_user, "email", None)
            servers = getattr(plex_user, "servers", []) or []

            if email and any(s.machineIdentifier == server_id for s in servers):
                users_by_email[email] = plex_user

        return users_by_email

    def _sync_user_permissions(self, user: User, plex_user) -> None:
        """Sync permissions and library access from Plex to database user."""
        # Update basic info
        user.username = getattr(plex_user, "title", user.username)
        user.photo = getattr(plex_user, "thumb", None)

        # Update permissions
        permissions = self._extract_plex_permissions(plex_user)
        user.is_admin = permissions["is_admin"]
        user.allow_downloads = permissions["allow_downloads"]
        user.allow_live_tv = permissions["allow_live_tv"]
        user.allow_camera_upload = permissions["allow_camera_upload"]

        # Update library access
        library_names, has_full_access = self._get_user_library_access(plex_user)
        if has_full_access:
            user.set_accessible_libraries(None)
        else:
            user.set_accessible_libraries(library_names or [])

    # ─── Library Access Methods ────────────────────────────────────────────────

    def _get_user_library_access(self, plex_user) -> tuple[list[str] | None, bool]:
        """Extract library access: (library_names | None, has_full_access)."""
        # Find this server's share
        matching_share = next(
            (
                s
                for s in getattr(plex_user, "servers", []) or []
                if getattr(s, "machineIdentifier", None)
                == self.server.machineIdentifier
            ),
            None,
        )

        if not matching_share:
            logging.warning(
                f"PLEX: No server share found for user {getattr(plex_user, 'email', 'unknown')}"
            )
            return [], False

        # Check if user has full access
        if getattr(matching_share, "allLibraries", False):
            return None, True

        return self._extract_library_names_from_share(matching_share), False

    def _extract_library_names_from_share(self, server_share) -> list[str]:
        """Extract library names from Plex server share object."""
        if not server_share:
            return []

        # Get sections (API varies by plexapi version)
        try:
            sections_data = server_share.sections()
        except (TypeError, AttributeError):
            sections_data = getattr(server_share, "sections", None)

        if not sections_data:
            return []

        # Handle callable sections
        if callable(sections_data):
            try:
                sections_data = sections_data()
            except Exception as exc:
                logging.warning(f"PLEX: Failed to call sections(): {exc}")
                return []

        # Extract library names (skip non-shared sections)
        return [
            section.title
            for section in sections_data or []
            if getattr(section, "title", None)
            and not (hasattr(section, "shared") and section.shared is False)
        ]

    def get_movie_posters(self, limit: int = 10) -> list[str]:
        """Get movie poster URLs for background display."""
        poster_urls = []
        try:
            # Get movie libraries
            for library in self.server.library.sections():
                if library.type == "movie":
                    # Get recent movies from this library
                    movies = library.recentlyAdded(maxresults=limit)
                    for movie in movies[:limit]:
                        poster_url = None

                        if hasattr(movie, "posterUrl") and movie.posterUrl:
                            poster_url = movie.posterUrl
                        elif hasattr(movie, "thumb") and movie.thumb:
                            # Fallback to thumb
                            poster_url = movie.thumb

                        if poster_url:
                            # Convert to full URL if needed
                            if poster_url.startswith("/"):
                                poster_url = f"{self.url.rstrip('/')}{poster_url}"

                            # Generate secure proxy URL with opaque token
                            proxied_url = self.generate_image_proxy_url(poster_url)
                            poster_urls.append(proxied_url)

                        if len(poster_urls) >= limit:
                            break

                    if len(poster_urls) >= limit:
                        break
        except Exception as e:
            # Log error but don't break the login process
            import logging

            logging.warning(f"Failed to fetch movie posters: {e}")

        return poster_urls[:limit]

    def get_recent_items(
        self, library_id: str | None = None, limit: int = 10
    ) -> list[dict]:
        """Get recently added items from Plex server."""
        try:
            items = []

            # Get all library sections or specific library if provided
            if library_id:
                try:
                    library = self.server.library.sectionByID(library_id)
                    libraries = [library] if library else []
                except Exception:
                    libraries = []
            else:
                libraries = list(self.server.library.sections())

            for library in libraries:
                if len(items) >= limit:
                    break

                try:
                    # Get recently added items from this library
                    recent_items = library.recentlyAdded(maxresults=limit - len(items))

                    for item in recent_items:
                        if len(items) >= limit:
                            break

                        # Only use posterUrl - skip items without proper posters
                        thumb_url = None
                        if hasattr(item, "posterUrl") and item.posterUrl:
                            thumb_url = item.posterUrl

                            # Convert relative URLs to full URLs
                            if thumb_url.startswith("/"):
                                thumb_url = f"{self.url.rstrip('/')}{thumb_url}"

                            # Generate secure proxy URL with opaque token
                            thumb_url = self.generate_image_proxy_url(thumb_url)

                            # Extract year from releaseDate
                            year = None
                            if hasattr(item, "year") and item.year:
                                year = item.year
                            elif (
                                hasattr(item, "originallyAvailableAt")
                                and item.originallyAvailableAt
                            ):
                                from contextlib import suppress

                                with suppress(Exception):
                                    year = item.originallyAvailableAt.year

                            # Get item type
                            item_type = getattr(item, "type", "unknown").lower()

                            # Get added date
                            added_at = None
                            if hasattr(item, "addedAt") and item.addedAt:
                                from contextlib import suppress

                                with suppress(Exception):
                                    # Convert to ISO format string like Jellyfin
                                    added_at = item.addedAt.isoformat() + "Z"

                            # Only add items that have poster images
                            items.append(
                                {
                                    "title": getattr(item, "title", "Unknown"),
                                    "year": year,
                                    "thumb": thumb_url,
                                    "type": item_type,
                                    "added_at": added_at,
                                }
                            )

                except Exception as exc:
                    logging.debug(f"Failed to process Plex media item: {exc}")
                    continue

            return items

        except Exception:
            return []

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        if url and token:
            try:
                from plexapi.server import PlexServer

                temp_server = PlexServer(url, token)
                return {lib.title: lib.title for lib in temp_server.library.sections()}
            except Exception as e:
                logging.error(f"Failed to scan Plex libraries: {e}")
                return {}
        else:
            return self.libraries()

    def create_user(self, *args, **kwargs):
        raise NotImplementedError(
            "PlexClient does not support create_user; use invite_friend or invite_home"
        )

    def _do_join(
        self, _username: str, _password: str, _confirm: str, _email: str, _code: str
    ) -> tuple[bool, str]:
        """Interface method - not implemented for Plex (uses OAuth instead)."""
        return (
            False,
            "Plex does not support direct user creation. Users must be invited via email.",
        )

    def invite_friend(
        self,
        email: str,
        sections: list[str],
        allow_sync: bool,
        allow_channels: bool,
        allow_camera_upload: bool = False,
    ):
        try:
            self.admin.inviteFriend(
                user=email,
                server=self.server,
                sections=sections,
                allowSync=allow_sync,
                allowChannels=allow_channels,
                allowCameraUpload=allow_camera_upload,
            )
        except Exception as e:
            # Extract human-readable error message and raise custom exception
            error_message = extract_plex_error_message(e)
            logging.error(f"Failed to invite friend {email}: {error_message}")
            raise PlexInvitationError(error_message, e) from e

    def invite_home(
        self,
        email: str,
        sections: list[str],
        allow_sync: bool,
        allow_channels: bool,
        allow_camera_upload: bool = False,
    ):
        try:
            self.admin.createExistingUser(
                user=email,
                server=self.server,
                sections=sections,
                allowSync=allow_sync,
                allowChannels=allow_channels,
                allowCameraUpload=allow_camera_upload,
            )
        except Exception as e:
            # Extract human-readable error message and raise custom exception
            error_message = extract_plex_error_message(e)
            logging.error(f"Failed to invite home user {email}: {error_message}")
            raise PlexInvitationError(error_message, e) from e

    def get_user(self, db_id: int) -> dict:
        """Get user info in legacy format for backward compatibility."""
        details = self.get_user_details(db_id)

        # Convert to legacy Plex format
        return {
            "Name": details.username,
            "Id": details.user_id,
            "Configuration": {
                "admin": details.is_admin,
                "allowSync": details.allow_downloads,
                "allowChannels": details.allow_live_tv,
                "allowCameraUpload": details.allow_camera_upload,
            },
            "Policy": {},
        }

    def get_user_details(self, db_id: int) -> "MediaUserDetails":
        """Get detailed user information from database (no API calls)."""
        from app.services.media.user_details import MediaUserDetails, UserLibraryAccess

        user = db.session.get(User, db_id)
        if not user:
            raise ValueError(f"No user found with id {db_id}")

        # Build library access from stored names
        library_names = user.get_accessible_libraries()
        library_access = None

        if library_names:
            libs_by_name = {
                lib.name: lib
                for lib in Library.query.filter(
                    Library.server_id == self.server_id,
                    Library.name.in_(library_names),
                ).all()
            }
            library_access = [
                UserLibraryAccess(
                    library_id=lib.external_id
                    if (lib := libs_by_name.get(name))
                    else f"plex_{name}",
                    library_name=name,
                    has_access=True,
                )
                for name in library_names
            ]

        return MediaUserDetails(
            user_id=str(user.id),
            username=user.username,
            email=user.email,
            is_admin=user.is_admin or False,
            is_enabled=True,
            created_at=None,
            last_active=None,
            allow_downloads=user.allow_downloads or False,
            allow_live_tv=user.allow_live_tv or False,
            allow_camera_upload=user.allow_camera_upload or False,
            library_access=library_access,
        )

    def update_user(self, info: dict, form: dict) -> None:
        self.admin.updateFriend(
            info["Name"],
            self.server,
            allowSync=bool(form.get("allowSync")),
            allowChannels=bool(form.get("allowChannels")),
            allowCameraUpload=bool(form.get("allowCameraUpload")),
        )

    def _get_all_library_global_ids(self) -> dict[str, int]:
        """Get mapping of all server libraries (name -> global ID).

        This fetches library information from the Plex server's own libraries endpoint,
        which includes the global library section IDs needed for the sharing API.

        Returns:
            dict: Mapping of library title to global ID {title: id}
        """
        try:
            base = "https://plex.tv"
            url = f"{base}/api/v2/servers/{self.server.machineIdentifier}"

            params = {
                "X-Plex-Product": "Wizarr",
                "X-Plex-Version": "1.0",
                "X-Plex-Client-Identifier": self.admin.uuid,
                "X-Plex-Token": self.admin.authToken,
                "X-Plex-Platform": "Web",
                "X-Plex-Features": "external-media,indirect-media,hub-style-list",
                "X-Plex-Language": "en",
            }

            headers = {"Accept": "application/json"}

            resp = self.admin._session.get(url, params=params, headers=headers)
            resp.raise_for_status()
            server_data = resp.json()

            # Extract libraries from server data (Plex uses 'librarySections' key)
            libraries = server_data.get("librarySections", [])

            library_map = {}

            for lib in libraries:
                title = lib.get("title")
                lib_id = lib.get("id")
                if title and lib_id:
                    library_map[title] = lib_id

            logging.debug(f"Found {len(library_map)} libraries with global IDs")
            return library_map

        except Exception as e:
            logging.error(f"Failed to get library global IDs: {e}", exc_info=True)
            return {}

    def _get_share_data(self, email: str) -> dict | None:
        """Get the complete share data for a user.

        Returns the full share object which includes the shared_server ID
        and the library mappings with their global IDs.

        Args:
            email: User's email address

        Returns:
            dict: The share data, or None if not found
        """
        try:
            # First, try to get the Plex user object to find their ID
            plex_user_id = None
            try:
                plex_user = self.admin.user(email)
                if plex_user:
                    plex_user_id = getattr(plex_user, "id", None)
            except Exception as exc:
                # If getting by email fails, might not exist or different identifier
                logging.debug(f"Could not get Plex user by email {email}: {exc}")

            # GET the list of owned/accepted shares
            base = "https://clients.plex.tv"
            url = f"{base}/api/v2/shared_servers/owned/accepted"

            params = {
                "X-Plex-Product": "Wizarr",
                "X-Plex-Version": "1.0",
                "X-Plex-Client-Identifier": self.admin.uuid,
                "X-Plex-Token": self.admin.authToken,
                "X-Plex-Platform": "Web",
                "X-Plex-Platform-Version": "1.0",
                "X-Plex-Features": "external-media,indirect-media,hub-style-list",
                "X-Plex-Language": "en",
            }

            headers = {"Accept": "application/json"}

            resp = self.admin._session.get(url, params=params, headers=headers)
            resp.raise_for_status()
            shared_servers = resp.json()

            # Find the share matching this server and user
            for share in shared_servers:
                # Check if this share is for our server
                if share.get("machineIdentifier") != self.server.machineIdentifier:
                    continue

                # Try matching by Plex user ID first (most reliable)
                if plex_user_id and share.get("invitedId") == plex_user_id:
                    return share

                # Fallback: Try matching by email/username
                invited = share.get("invited", {})
                invited_email = (
                    invited.get("email")
                    or invited.get("username")
                    or share.get("invitedEmail")
                )

                if invited_email and invited_email.lower() == email.lower():
                    return share

            logging.warning(
                f"No shared_server found for {email} on server {self.server.friendlyName}"
            )
            return None
        except Exception as e:
            logging.error(f"Failed to get share data for {email}: {e}")
            return None

    def _get_shared_server_id(self, email: str) -> int | None:
        """Get the shared_server ID from the admin's perspective."""
        share = self._get_share_data(email)
        return share.get("id") if share else None

    def _get_current_plex_state(self, email: str) -> tuple[dict, list | None]:
        """Get current permissions and library access for a Plex user.

        Args:
            email: User's email address

        Returns:
            Tuple of (permissions_dict, sections_list)
            permissions_dict has keys: allow_downloads, allow_live_tv, allow_camera_upload
            sections_list is either None or a list of LibrarySection objects
        """
        plex_user = self.admin.user(email)
        if not plex_user:
            raise ValueError(f"Plex user not found: {email}")

        # Extract current permissions
        permissions = self._extract_plex_permissions(plex_user)

        # Find this server's share for the user
        matching_share = next(
            (
                s
                for s in getattr(plex_user, "servers", []) or []
                if getattr(s, "machineIdentifier", None)
                == self.server.machineIdentifier
            ),
            None,
        )

        # Get current sections (libraries) for this user
        sections = None
        if matching_share:
            library_names = self._extract_library_names_from_share(matching_share)
            # Convert library names to section objects
            if library_names:
                all_sections = self.server.library.sections()
                sections = [s for s in all_sections if s.title in library_names]

        return permissions, sections

    def update_user_permissions(self, email: str, permissions: dict[str, bool]) -> bool:
        """Update user permissions on Plex using the shared_servers API.

        Args:
            email: User's email address
            permissions: Dict with keys: allow_downloads, allow_live_tv, allow_camera_upload

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the shared_server ID
            shared_server_id = self._get_shared_server_id(email)
            if not shared_server_id:
                logging.error(f"Could not find shared_server ID for {email}")
                return False

            # Get current library section IDs to preserve them
            # Use share data to get the global library IDs
            share = self._get_share_data(email)
            if not share:
                logging.error(f"Could not get share data for {email}")
                return False

            section_ids = [lib["id"] for lib in share.get("libraries", [])]

            # Build settings with new permissions
            settings = {
                "allowSync": permissions.get("allow_downloads", False),
                "allowChannels": permissions.get("allow_live_tv", False),
                "allowCameraUpload": permissions.get("allow_camera_upload", False),
                "filterMovies": "",
                "filterMusic": "",
                "filterPhotos": None,
                "filterTelevision": "",
                "filterAll": None,
                "allowSubtitleAdmin": False,
                "allowTuners": 0,
            }

            # Call the custom API method
            success = update_shared_server(
                self.admin, shared_server_id, settings, section_ids
            )

            if success:
                logging.info(
                    f"Successfully updated permissions for {email} via shared_servers API"
                )

            return success
        except Exception as e:
            logging.error(f"Failed to update permissions for {email}: {e}")
            return False

    def update_user_libraries(
        self, email: str, library_names: list[str] | None
    ) -> bool:
        """Update user's library access on Plex using the shared_servers API.

        Args:
            email: User's email address
            library_names: List of library names to grant access to, or None for all libraries

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the shared_server ID
            shared_server_id = self._get_shared_server_id(email)
            if not shared_server_id:
                logging.error(f"Could not find shared_server ID for {email}")
                return False

            # Get current permissions to preserve them
            current_perms, _ = self._get_current_plex_state(email)

            # Get the share data to access library ID mappings
            share = self._get_share_data(email)
            if not share:
                logging.error(f"Could not get share data for {email}")
                return False

            # Log current share state
            current_libs = share.get("libraries", [])
            logging.info(
                f"Current libraries in share: {[lib['title'] for lib in current_libs]}"
            )
            logging.info(
                f"Current library IDs in share: {[lib['id'] for lib in current_libs]}"
            )

            # Get library global IDs from database (external_id stores the global ID)
            # This assumes libraries have been scanned and stored correctly
            from app.models import Library

            section_ids = []
            if library_names is not None:
                logging.info(f"Requested libraries: {library_names}")
                libraries = (
                    Library.query.filter_by(server_id=self.server_id)
                    .filter(Library.name.in_(library_names))
                    .all()
                )

                for lib in libraries:
                    section_ids.append(int(lib.external_id))
                    logging.info(f"  ✓ {lib.name} -> {lib.external_id}")

                # Check for missing libraries
                found_names = {lib.name for lib in libraries}
                missing = set(library_names) - found_names
                for name in missing:
                    logging.warning(
                        f"  ✗ Library '{name}' not found in database (scan libraries to fix)"
                    )

                logging.info(f"Converted to section IDs: {section_ids}")
            else:
                # None means all libraries - get all enabled libraries for this server
                libraries = Library.query.filter_by(
                    server_id=self.server_id, enabled=True
                ).all()
                section_ids = [int(lib.external_id) for lib in libraries]
                logging.info(f"Using all library IDs: {section_ids}")

            # Build settings with preserved permissions
            settings = {
                "allowSync": current_perms["allow_downloads"],
                "allowChannels": current_perms["allow_live_tv"],
                "allowCameraUpload": current_perms["allow_camera_upload"],
                "filterMovies": "",
                "filterMusic": "",
                "filterPhotos": None,
                "filterTelevision": "",
                "filterAll": None,
                "allowSubtitleAdmin": False,
                "allowTuners": 0,
            }

            # Call the custom API method
            success = update_shared_server(
                self.admin, shared_server_id, settings, section_ids
            )

            if success:
                logging.info(
                    f"Successfully updated library access for {email} via shared_servers API"
                )

            return success
        except Exception as e:
            logging.error(f"Failed to update library access for {email}: {e}")
            return False

    def enable_user(self, _user_id: str) -> bool:
        """Enable a user account on Plex.

        Args:
            _user_id: The user's Plex ID (unused - Plex doesn't support enable/disable)

        Returns:
            bool: True if the user was successfully enabled, False otherwise
        """
        try:
            # Plex doesn't have a direct disable/enable feature
            # Return False to indicate this operation is not supported
            structlog.get_logger().warning(
                "Plex does not support disabling/enabling users"
            )
            return False
        except Exception as e:
            structlog.get_logger().error(f"Failed to enable Plex user: {e}")
            return False

    def disable_user(self, user_id: str) -> bool:
        """Disable a user account on Plex.

        Note: Plex doesn't have a direct disable feature for managed users.
        This implementation removes all library access which effectively disables the account.

        Args:
            user_id: The user's Plex ID

        Returns:
            bool: True if the user was successfully disabled, False otherwise
        """
        try:
            # For Plex, we remove all library access to effectively disable the user
            user = self.admin.user(user_id)
            if user:
                user.removeFriend()
                return True
            return False
        except Exception as e:
            structlog.get_logger().error(f"Failed to disable Plex user: {e}")
            return False

    def delete_user(self, email: str) -> None:
        """Remove a user from the Plex server."""
        try:
            self.admin.removeHomeUser(email)
        except Exception:
            try:
                self.admin.removeFriend(email)
            except Exception as e:
                logging.error("Error removing friend: %s", e)

    @cached(cache=TTLCache(maxsize=1024, ttl=600))
    def list_users(self) -> list[User]:
        """Sync users from Plex to database with all permissions and library access."""
        try:
            admin_users = self.admin.users()
        except (ConnectionError, Exception) as e:
            logging.error(f"Failed to connect to Plex admin API: {e}")
            return self._get_server_users()

        plex_users_by_email = self._filter_users_for_server(
            admin_users, self.server.machineIdentifier
        )

        # Remove users no longer in Plex, add new users
        known_emails = set(plex_users_by_email.keys())
        for db_user in self._get_server_users():
            if db_user.email not in known_emails:
                db.session.delete(db_user)

        for email, plex_user in plex_users_by_email.items():
            if not User.query.filter_by(email=email, server_id=self.server_id).first():
                db.session.add(
                    User(
                        email=email,
                        username=getattr(plex_user, "title", "Unknown"),
                        token="None",  # noqa: S106  # Placeholder string, not actual password
                        code="None",
                        server_id=self.server_id,
                    )
                )

        # Sync all permissions and library access
        for user in self._get_server_users():
            if plex_user := plex_users_by_email.get(user.email):
                self._sync_user_permissions(user, plex_user)

        try:
            db.session.commit()
            logging.info(f"Synced {len(plex_users_by_email)} Plex users to database")
        except Exception as e:
            logging.error(f"Failed to sync Plex user metadata: {e}")
            db.session.rollback()

        return self._get_server_users()

    def _get_user_identifier_for_details(self, user: User) -> str | int | None:
        """Plex uses database ID for get_user_details."""
        return user.id

    def now_playing(self) -> list[dict]:
        try:
            sessions = self.server.sessions()
            now_playing_sessions = []

            for session in sessions:
                view_offset = getattr(session, "viewOffset", None)
                if view_offset is None:
                    continue

                progress = 0.0
                duration = getattr(session, "duration", None)
                if duration and view_offset:
                    progress = max(0.0, min(1.0, view_offset / duration))

                media_type = getattr(session, "type", "unknown").lower()

                media_title = getattr(session, "title", "Unknown")
                if media_type == "episode":
                    grandparent_title = getattr(session, "grandparentTitle", "")
                    season_num = getattr(session, "parentIndex", None)
                    episode_num = getattr(session, "index", None)
                    if grandparent_title:
                        media_title = f"{grandparent_title}"
                        if season_num and episode_num:
                            media_title += f" S{season_num:02d}E{episode_num:02d}"
                        media_title += f" - {getattr(session, 'title', '')}"

                players = getattr(session, "players", [])
                state = "stopped"
                if players:
                    player_state = getattr(players[0], "state", "stopped")
                    state = {
                        "paused": "paused",
                        "playing": "playing",
                        "buffering": "buffering",
                    }.get(player_state, "stopped")

                user_info = "Unknown User"
                usernames = getattr(session, "usernames", None)
                users = getattr(session, "users", None)
                if usernames:
                    user_info = usernames[0]
                elif users:
                    user_info = users[0].title

                client_name = device_name = ""
                if players:
                    client_name = getattr(players[0], "product", "")
                    device_name = getattr(players[0], "title", "")

                artwork_url = None
                images_attr = getattr(session, "image", None)
                if images_attr:
                    images_list = (
                        images_attr
                        if isinstance(images_attr, list | tuple | set)
                        else [images_attr]
                    )
                    for img in images_list:
                        if getattr(img, "type", None) == "coverPoster":
                            img_key = getattr(img, "key", None) or getattr(
                                img, "thumb", None
                            )
                            if img_key:
                                artwork_url = (
                                    img_key
                                    if str(img_key).startswith("http")
                                    else self.server.url(img_key, includeToken=True)
                                )
                            elif getattr(img, "thumbUrl", None):
                                artwork_url = img.thumbUrl
                            elif getattr(img, "url", None):
                                artwork_url = img.url
                            if artwork_url:
                                break

                for attr in ("grandparentThumb", "parentThumb", "art"):
                    if artwork_url is not None:
                        break
                    val = getattr(session, attr, None)
                    if val:
                        artwork_url = (
                            val
                            if str(val).startswith("http")
                            else self.server.url(val, includeToken=True)
                        )

                thumb_url = getattr(session, "thumbUrl", None)
                if artwork_url is None and thumb_url:
                    artwork_url = thumb_url

                # Check for transcoding using Plex API structure
                is_transcoding = False
                transcode_speed = None
                media_list = getattr(session, "media", [])

                # Method 1: Check for TranscodeSession using python-plexapi properties
                # This is the most reliable method as it directly reflects the actual transcoding state
                transcode_session = getattr(session, "transcodeSession", None)
                if transcode_session:
                    # TranscodeSession object has videoDecision and audioDecision attributes
                    video_decision = getattr(transcode_session, "videoDecision", None)
                    audio_decision = getattr(transcode_session, "audioDecision", None)

                    # Only consider it transcoding if either video or audio is actually being transcoded
                    # "copy" and "direct" mean no transcoding is happening
                    if video_decision == "transcode" or audio_decision == "transcode":
                        is_transcoding = True
                        transcode_speed = getattr(transcode_session, "speed", None)

                # Method 2: Check transcodeSessions list property (fallback)
                if not is_transcoding and not transcode_session:
                    transcode_sessions = getattr(session, "transcodeSessions", [])
                    if transcode_sessions:
                        # Check each transcode session for actual transcoding
                        for ts in transcode_sessions:
                            ts_video_decision = getattr(ts, "videoDecision", None)
                            ts_audio_decision = getattr(ts, "audioDecision", None)
                            if (
                                ts_video_decision == "transcode"
                                or ts_audio_decision == "transcode"
                            ):
                                is_transcoding = True
                                transcode_speed = getattr(ts, "speed", None)
                                break

                video_codec = audio_codec = container = video_resolution = None
                if media_list:
                    media_obj = media_list[0]
                    video_codec = getattr(media_obj, "videoCodec", None)
                    audio_codec = getattr(media_obj, "audioCodec", None)
                    container = getattr(media_obj, "container", None)
                    video_resolution = getattr(media_obj, "videoResolution", None)

                transcoding_info = {
                    "is_transcoding": is_transcoding,
                    "video_codec": video_codec,
                    "audio_codec": audio_codec,
                    "container": container,
                    "video_resolution": video_resolution,
                    "transcoding_speed": transcode_speed,
                    "direct_play": not is_transcoding,
                }

                session_info = {
                    "user_name": user_info,
                    "media_title": media_title,
                    "media_type": media_type,
                    "progress": progress,
                    "state": state,
                    "session_id": str(getattr(session, "sessionKey", "")),
                    "client": client_name,
                    "device_name": device_name,
                    "position_ms": getattr(session, "viewOffset", 0),
                    "duration_ms": getattr(session, "duration", 0),
                    "artwork_url": artwork_url,
                    "transcoding_info": transcoding_info,
                    "thumbnail_url": getattr(session, "thumbUrl", None),
                }

                now_playing_sessions.append(session_info)

            return now_playing_sessions

        except Exception as e:
            logging.error(f"Failed to get now playing from Plex: {e}")
            return []

    def statistics(self):
        try:
            stats = {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
            }

            # Try to get session information from the local server
            try:
                sessions = self.server.sessions()
                transcode_sessions = self.server.transcodeSessions()
            except Exception as e:
                logging.warning(f"Failed to get Plex session info: {e}")
                sessions = []
                transcode_sessions = []

            # Try to get user stats - this is where the SSL error occurs
            try:
                users = self.list_users()
                stats["user_stats"] = {
                    "total_users": len(users),
                    "active_sessions": len(sessions),
                }
            except (ConnectionError, Exception) as e:
                logging.error(f"Failed to get Plex user stats: {e}")
                stats["user_stats"] = {
                    "total_users": 0,
                    "active_sessions": len(sessions),
                    "connection_error": "Unable to connect to Plex.tv servers",
                }

            # Try to get server stats
            try:
                stats["server_stats"] = {
                    "version": getattr(self.server, "version", "Unknown"),
                    "transcoding_sessions": len(transcode_sessions),
                }
            except Exception as e:
                logging.error(f"Failed to get Plex server stats: {e}")
                stats["server_stats"] = {
                    "version": "Unknown",
                    "transcoding_sessions": 0,
                    "error": str(e),
                }

            return stats

        except Exception as e:
            logging.error(f"Failed to get Plex statistics: {e}")
            return {
                "library_stats": {},
                "user_stats": {"total_users": 0, "active_sessions": 0},
                "server_stats": {"version": "Unknown", "transcoding_sessions": 0},
                "content_stats": {},
                "error": str(e),
            }

    def get_user_count(self) -> int:
        """Get lightweight user count from database without triggering Plex.tv sync."""
        try:
            # Count existing users in database for this server instead of calling list_users()
            from app.models import MediaServer, User

            if hasattr(self, "server_id") and self.server_id:
                count = User.query.filter_by(server_id=self.server_id).count()
            else:
                # Fallback for legacy settings: find MediaServer for this server type
                servers = MediaServer.query.filter_by(server_type="plex").all()
                if servers:
                    server_ids = [s.id for s in servers]
                    count = User.query.filter(User.server_id.in_(server_ids)).count()
                else:
                    # Ultimate fallback: try Plex API (expensive)
                    try:
                        users = self.list_users()
                        count = len(users) if users else 0
                    except Exception as api_error:
                        logging.warning(f"Plex API fallback failed: {api_error}")
                        count = 0
            return count
        except Exception as e:
            logging.error(f"Failed to get Plex user count from database: {e}")
            return 0

    def get_server_info(self) -> dict:
        """Get lightweight server information without triggering user sync."""
        try:
            # Get basic server info and session counts without calling list_users()
            sessions = []
            transcode_sessions = []

            try:
                sessions = self.server.sessions()
                transcode_sessions = self.server.transcodeSessions()
            except Exception as e:
                logging.warning(f"Failed to get Plex session info: {e}")

            return {
                "version": getattr(self.server, "version", "Unknown"),
                "transcoding_sessions": len(transcode_sessions),
                "active_sessions": len(sessions),
            }
        except Exception as e:
            logging.error(f"Failed to get Plex server info: {e}")
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
                "library_stats": {},  # Minimal for health cards
                "content_stats": {},  # Minimal for health cards
            }
        except Exception as e:
            logging.error(f"Failed to get Plex readonly statistics: {e}")
            return {
                "user_stats": {"total_users": 0, "active_sessions": 0},
                "server_stats": {"version": "Unknown", "transcoding_sessions": 0},
                "library_stats": {},
                "content_stats": {},
                "error": str(e),
            }


# ─── Invite & onboarding ────────────────────────────────────────────────


def handle_oauth_token(app, token: str, code: str) -> None:
    with app.app_context():
        account = MyPlexAccount(token=token)
        email = account.email

        inv = Invitation.query.filter_by(code=code).first()
        # Use the new multi-server relationship instead of legacy server
        if inv and inv.servers:
            # Get the first Plex server from the invitation's server list
            plex_servers = [s for s in inv.servers if s.server_type == "plex"]
            server = plex_servers[0] if plex_servers else inv.servers[0]
        elif inv and inv.server:
            # Fallback to legacy single server relationship
            server = inv.server
        else:
            # Last resort fallback
            server = MediaServer.query.first()
        if not server:
            raise ValueError("No media server found")
        server_id = server.id

        db.session.query(User).filter(
            User.email == email, User.server_id == server_id
        ).delete(synchronize_session=False)
        db.session.commit()

        from app.services.expiry import calculate_user_expiry

        expires = calculate_user_expiry(inv, server_id) if inv else None

        client = PlexClient(media_server=server)
        new_user = client._create_user_with_identity_linking(
            {
                "token": token,
                "email": email,
                "username": account.username,
                "code": code,
                "expires": expires,
                "server_id": server_id,
            }
        )
        db.session.commit()

        _invite_user(email, code, new_user.id, server)

        # Mark invitation as used for this server
        if inv:
            from app.services.invites import mark_server_used

            mark_server_used(inv, server_id, new_user)

        notify(
            "User Joined",
            f"User {account.username} has joined your server!",
            "tada",
            event_type="user_joined",
        )

        # Pass only what we need: server credentials and Flask app instance
        # Use the specific server that was determined for this invitation
        from flask import current_app

        post_setup_client = PlexClient(media_server=server)
        server_url = post_setup_client.url
        api_token = post_setup_client.token
        threading.Thread(
            target=_post_join_setup,
            args=(current_app._get_current_object(), server_url, api_token, token),  # type: ignore
            daemon=True,
        ).start()


def _invite_user(email: str, code: str, _user_id: int, server: MediaServer) -> None:
    inv = Invitation.query.filter_by(code=code).first()
    if not inv:
        raise ValueError(f"No invitation found with code {code}")

    client = get_client_for_media_server(server)

    libs = (
        [lib.external_id for lib in inv.libraries if lib.server_id == server.id]
        if inv.libraries
        else []
    )

    if not libs:
        libs = [
            lib.external_id
            for lib in Library.query.filter_by(enabled=True, server_id=server.id).all()
        ]

    allow_sync = bool(inv.allow_downloads)
    allow_tv = bool(inv.allow_live_tv)
    allow_camera_upload = bool(inv.allow_mobile_uploads)

    try:
        if inv.plex_home:
            client.invite_home(email, libs, allow_sync, allow_tv, allow_camera_upload)
        else:
            client.invite_friend(email, libs, allow_sync, allow_tv, allow_camera_upload)
    except PlexInvitationError:
        # Re-raise PlexInvitationError to preserve the user-friendly message
        raise
    except Exception as e:
        # Handle any other unexpected errors
        error_message = extract_plex_error_message(e)
        logging.error(f"Unexpected error inviting {email} to Plex: {error_message}")
        raise PlexInvitationError(error_message, e) from e

    logging.info("Invited %s to Plex", email)

    PlexClient.list_users.cache_clear()
    db.session.commit()


def _post_join_setup(app, server_url: str, api_token: str, token: str):
    # Create a PlexServer instance with Flask app context
    from plexapi.server import PlexServer

    with app.app_context():
        try:
            server = PlexServer(server_url, api_token)
            user = MyPlexAccount(token=token)
            # use username as the v2 API returns only username, not e-mail
            admin_account = server.myPlexAccount()
            user.acceptInvite(admin_account.username)
            user.enableViewStateSync()
            _opt_out_online_sources(user)
        except ValueError as exc:
            if "No pending invite" in str(exc):
                # This is expected - the invite was already accepted in the main flow
                logging.info(
                    "Invite already accepted, proceeding with remaining setup: %s", exc
                )
                try:
                    # Still try to enable view state sync and opt out of online sources
                    user = MyPlexAccount(token=token)
                    user.enableViewStateSync()
                    _opt_out_online_sources(user)
                except Exception as setup_exc:
                    logging.warning("Partial post-join setup failed: %s", setup_exc)
            else:
                logging.error("Post-join setup failed with ValueError: %s", exc)
        except Exception as exc:
            logging.error("Post-join setup failed: %s", exc)


def _opt_out_online_sources(user: MyPlexAccount):
    online_sources = user.onlineMediaSources()
    for src in online_sources:
        if src and hasattr(src, "optOut"):
            src.optOut()


# ─── User queries / mutate ────────────────────────────────────────────────
