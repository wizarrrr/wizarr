import logging
import re
import threading
from typing import TYPE_CHECKING

import structlog
from cachetools import TTLCache, cached
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer

from app.extensions import db
from app.models import Invitation, Library, MediaServer, User
from app.services.media.service import get_client_for_media_server
from app.services.notifications import notify

from .client_base import MediaClient, register_media_client

if TYPE_CHECKING:
    from app.services.media.user_details import MediaUserDetails


def _accept_invite_v2(self: MyPlexAccount, user):
    """Accept a pending server share via the v2 API."""
    base = "https://clients.plex.tv"

    params = {
        k: v
        for k, v in self._session.headers.items()
        if k.startswith("X-Plex-") and k != "X-Plex-Provides"
    }

    defaults = {
        "X-Plex-Product": "Wizarr",
        "X-Plex-Version": "1.0",
        "X-Plex-Client-Identifier": "wizarr-client",
        "X-Plex-Platform": "Python",
        "X-Plex-Platform-Version": "3",
        "X-Plex-Device": "Server",
        "X-Plex-Device-Name": "Wizarr",
        "X-Plex-Model": "server",
        "X-Plex-Device-Screen-Resolution": "1920x1080",
        "X-Plex-Features": "external-media,indirect-media,hub-style-list",
        "X-Plex-Language": "en",
    }

    for key, value in defaults.items():
        params.setdefault(key, value)

    params["X-Plex-Token"] = self.authToken
    hdrs = {"Accept": "application/json"}

    url_list = f"{base}/api/v2/shared_servers/invites/received/pending"
    resp = self._session.get(url_list, params=params, headers=hdrs)
    resp.raise_for_status()
    invites = resp.json()

    def _matches(inv):
        o = inv.get("owner", {})
        return user in (
            o.get("username"),
            o.get("email"),
            o.get("title"),
            o.get("friendlyName"),
        )

    try:
        inv = next(i for i in invites if _matches(i))
    except StopIteration as exc:
        raise ValueError(f"No pending invite from '{user}' found") from exc

    shared_servers = inv.get("sharedServers")
    if not shared_servers:
        raise ValueError("Invite structure missing 'sharedServers' list")

    invite_id = shared_servers[0]["id"]

    url_accept = f"{base}/api/v2/shared_servers/{invite_id}/accept"
    resp = self._session.post(url_accept, params=params, headers=hdrs)
    resp.raise_for_status()
    return resp


MyPlexAccount.acceptInvite = _accept_invite_v2  # type: ignore[assignment]


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
            kwargs["token_key"] = "api_key"

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
        return {lib.title: lib.title for lib in self.server.library.sections()}

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

                            # Use image proxy for external access
                            import urllib.parse

                            proxied_url = f"/image-proxy?url={urllib.parse.quote_plus(poster_url)}"
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
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
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
        return {
            "Name": details.username,
            "Id": details.user_id,
            "Configuration": details.raw_policies,
            "Policy": {},
        }

    def get_user_details(self, db_id: int) -> "MediaUserDetails":
        """Get detailed user information in standardized format."""
        from app.models import Library
        from app.services.media.user_details import MediaUserDetails, UserLibraryAccess

        user_record = User.query.get(db_id)
        if not user_record:
            raise ValueError(f"No user found with id {db_id}")

        plex_user = self.admin.user(user_record.email)
        if not plex_user:
            raise ValueError(f"Plex user not found for email {user_record.email}")

        # Extract library access from Plex user
        sections = []

        try:
            # Get the user's accessible libraries on this server
            for user_server in plex_user.servers:
                if user_server.machineIdentifier == self.server.machineIdentifier:
                    # Get sections from Plex user server
                    try:
                        sections = [section.title for section in user_server.sections()]
                        break
                    except TypeError:
                        # Fallback for different PlexAPI versions
                        try:
                            sections_data = user_server.sections()
                            sections = [section.title for section in sections_data]
                            break
                        except Exception:
                            sections_attr = user_server.sections
                            if hasattr(sections_attr, "__iter__"):
                                sections = [
                                    getattr(section, "title", str(section))
                                    for section in sections_attr
                                ]
                            break
        except Exception as e:
            logging.error(f"Failed to get Plex user sections: {e}")
            sections = []

        # Convert section titles to library access objects
        if sections:
            # Query our database to find matching libraries
            libs_q = (
                Library.query.filter(
                    Library.name.in_(sections),
                    Library.server_id == self.server_id,
                )
                .order_by(Library.name)
                .all()
            )
            library_access = [
                UserLibraryAccess(
                    library_id=lib.external_id, library_name=lib.name, has_access=True
                )
                for lib in libs_q
            ]

            # If we have sections but no matching libraries in DB, create them from section names
            if not library_access and sections:
                library_access = [
                    UserLibraryAccess(
                        library_id=f"plex_{i}", library_name=section, has_access=True
                    )
                    for i, section in enumerate(sections)
                ]
        else:
            # No sections found means user has access to all libraries
            library_access = None

        # Extract standardized permissions from Plex user
        is_admin = getattr(plex_user, "admin", False)
        allow_downloads = getattr(plex_user, "allowSync", True)
        allow_live_tv = getattr(plex_user, "allowChannels", True)
        allow_camera_upload = getattr(plex_user, "allowCameraUpload", False)

        return MediaUserDetails(
            user_id=str(plex_user.id),
            username=plex_user.title,
            email=plex_user.email,
            is_admin=is_admin,
            is_enabled=True,  # Plex doesn't have a disabled state for shared users
            created_at=None,  # Plex API doesn't provide creation date for shared users
            last_active=None,  # Plex API doesn't provide last active for shared users
            allow_downloads=allow_downloads,
            allow_live_tv=allow_live_tv,
            allow_camera_upload=allow_camera_upload,
            library_access=library_access,
            raw_policies={
                "admin": is_admin,
                "allowCameraUpload": allow_camera_upload,
                "allowChannels": allow_live_tv,
                "allowSync": allow_downloads,
            },
        )

    def update_user(self, info: dict, form: dict) -> None:
        self.admin.updateFriend(
            info["Name"],
            self.server,
            allowSync=bool(form.get("allowSync")),
            allowChannels=bool(form.get("allowChannels")),
            allowCameraUpload=bool(form.get("allowCameraUpload")),
        )

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
            user = self.my_account.user(user_id)
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
        """Sync users from Plex into the local DB and return the list of User records."""
        server_id = self.server.machineIdentifier

        try:
            admin_users = self.admin.users()
        except (ConnectionError, Exception) as e:
            logging.error(f"Failed to connect to Plex admin API: {e}")
            # Return existing DB users if we can't connect to Plex
            return (
                db.session.query(User)
                .filter(User.server_id == getattr(self, "server_id", None))
                .all()
            )

        plex_users = {}
        for u in admin_users:
            user_email = getattr(u, "email", None)
            user_servers = getattr(u, "servers", None) or []
            if user_email and any(
                s.machineIdentifier == server_id for s in user_servers
            ):
                plex_users[user_email] = u

        db_users = (
            db.session.query(User)
            .filter(
                db.or_(
                    User.server_id.is_(None),
                    User.server_id == getattr(self, "server_id", None),
                )
            )
            .all()
        )

        known_emails = set(plex_users.keys())
        for db_user in db_users:
            if db_user.email not in known_emails:
                db.session.delete(db_user)
        db.session.commit()

        for plex_user in plex_users.values():
            user_email = getattr(plex_user, "email", None) or "None"
            user_title = getattr(plex_user, "title", None) or "Unknown"
            existing = (
                db.session.query(User)
                .filter_by(email=user_email, server_id=getattr(self, "server_id", None))
                .first()
            )
            if not existing:
                new_user = User(
                    email=user_email,
                    username=user_title,
                    token="None",
                    code="None",
                    server_id=getattr(self, "server_id", None),
                )
                db.session.add(new_user)
        db.session.commit()

        users = (
            db.session.query(User)
            .filter(User.server_id == getattr(self, "server_id", None))
            .all()
        )

        # Update user metadata using the metadata caching system
        for u in users:
            p = plex_users.get(u.email)
            if p:
                u.photo = p.thumb

                # Store Plex permissions in raw_policies_json using the proper method
                plex_policies = {
                    "admin": getattr(p, "admin", False),
                    "allowCameraUpload": getattr(p, "allowCameraUpload", False),
                    "allowChannels": getattr(p, "allowChannels", True),
                    "allowSync": getattr(p, "allowSync", True),
                    # Map Plex permissions to common permission names for display
                    "allow_downloads": getattr(
                        p, "allowSync", True
                    ),  # Sync permission in Plex
                    "allow_live_tv": getattr(
                        p, "allowChannels", True
                    ),  # Channel/Live TV access
                }
                u.set_raw_policies(plex_policies)
            else:
                # Default values if Plex user data not found - store in metadata too
                default_policies = {
                    "admin": False,
                    "allowCameraUpload": False,
                    "allowChannels": False,
                    "allowSync": False,
                    "allow_downloads": False,
                    "allow_live_tv": False,
                }
                u.set_raw_policies(default_policies)

        # Single commit for all permission changes to reduce lock time
        try:
            db.session.commit()
        except Exception as e:
            logging.error(f"Failed to update Plex user metadata: {e}")
            db.session.rollback()
            # Continue without metadata updates rather than failing completely

        # Cache detailed metadata for all users from bulk response (no individual API calls)
        self._cache_user_metadata_from_bulk_response(users, plex_users)

        return users

    def _cache_user_metadata_from_bulk_response(
        self, users: list[User], plex_users: dict
    ) -> None:
        """Cache user metadata from bulk API response without individual API calls.

        Args:
            users: List of User objects to cache metadata for
            plex_users: Dictionary of plex user objects from bulk admin.users() call
        """
        if not users or not plex_users:
            return

        cached_count = 0
        for user in users:
            try:
                # Get the plex user object from bulk response
                plex_user = plex_users.get(user.email)
                if not plex_user:
                    continue

                # Extract standardized metadata from bulk response
                from app.services.media.user_details import (
                    MediaUserDetails,
                    UserLibraryAccess,
                )

                # Extract library access from Plex user
                sections = []
                try:
                    # Get sections the user has access to
                    if hasattr(plex_user, "servers") and plex_user.servers:
                        for server in plex_user.servers:
                            if (
                                server.machineIdentifier
                                == self.server.machineIdentifier
                            ):
                                # Get sections from Plex user server
                                try:
                                    sections = [
                                        section.title for section in server.sections()
                                    ]
                                    break
                                except TypeError:
                                    # Fallback for different PlexAPI versions
                                    try:
                                        sections_data = server.sections()
                                        sections = [
                                            section.title for section in sections_data
                                        ]
                                        break
                                    except Exception:
                                        sections_attr = server.sections
                                        if hasattr(sections_attr, "__iter__"):
                                            sections = [
                                                getattr(section, "title", str(section))
                                                for section in sections_attr
                                            ]
                                        break
                except Exception as e:
                    logging.warning(
                        f"Failed to get sections for user {user.email}: {e}"
                    )
                    sections = []

                # Extract standardized permissions from Plex user
                is_admin = getattr(plex_user, "admin", False)
                allow_downloads = getattr(plex_user, "allowSync", True)
                allow_live_tv = getattr(plex_user, "allowChannels", True)
                allow_camera_upload = getattr(plex_user, "allowCameraUpload", False)

                # Create MediaUserDetails object with standardized data
                details = MediaUserDetails(
                    user_id=str(user.id),  # Plex uses database ID for details
                    username=getattr(plex_user, "title", user.username),
                    email=getattr(plex_user, "email", user.email),
                    is_admin=is_admin,
                    is_enabled=True,  # Plex users are enabled if they exist
                    created_at=None,  # Plex doesn't provide creation date in bulk response
                    last_active=None,  # Plex doesn't provide last active in bulk response
                    allow_downloads=allow_downloads,
                    allow_live_tv=allow_live_tv,
                    allow_camera_upload=allow_camera_upload,
                    library_access=None
                    if not sections
                    else [
                        UserLibraryAccess(
                            library_id=f"plex_{i}",
                            library_name=section,
                            has_access=True,
                        )
                        for i, section in enumerate(sections)
                    ],
                    raw_policies={
                        "admin": is_admin,
                        "allowCameraUpload": allow_camera_upload,
                        "allowChannels": allow_live_tv,
                        "allowSync": allow_downloads,
                    },
                )

                # Update user with standardized metadata columns
                user.update_standardized_metadata(details)
                cached_count += 1

            except Exception as e:
                logging.warning(f"Failed to cache metadata for user {user.email}: {e}")
                continue

        if cached_count > 0:
            logging.info(f"Updated standardized metadata for {cached_count} users")

        # Commit the standardized metadata updates
        try:
            db.session.commit()
        except Exception as e:
            logging.error(f"Failed to commit standardized metadata: {e}")
            db.session.rollback()

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
                    "transcoding": transcoding_info,
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
            "User Joined", f"User {account.username} has joined your server!", "tada"
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


def _invite_user(email: str, code: str, user_id: int, server: MediaServer) -> None:
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
