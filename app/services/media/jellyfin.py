import logging
from collections.abc import Collection
from typing import TYPE_CHECKING, Any

import requests
import structlog
from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, Library, MediaServer, User
from app.services.invites import is_invite_valid

from .auth_headers import media_browser_auth_headers
from .client_base import (
    EMAIL_RE,
    ClientCapabilities,
    RestApiMixin,
    register_media_client,
)
from .utils import library_name_selected, newest_first

if TYPE_CHECKING:
    from app.services.media.user_details import MediaUserDetails

# Resized image requests. Jellyfin and Emby both accept maxWidth, maxHeight
# and quality, and they only make an image smaller, never larger.
# The join page shows posters at about 120x160 px. 240 px wide is sharp on a
# 2x display.
POSTER_IMAGE_PARAMS = "maxWidth=240&quality=80"
# The now-playing card shows the poster at about 128x192 px.
NOW_PLAYING_POSTER_PARAMS = "maxHeight=400&quality=85"
# The now-playing card shows the backdrop blurred, so a small image is enough.
NOW_PLAYING_BACKDROP_PARAMS = "maxWidth=480&quality=60"


def login_screen_policy(server: MediaServer | None) -> dict[str, bool]:
    """Return the policy field that shows or hides a new user on login screens.

    Only Jellyfin servers use the option. Jellyfin hides new users by default,
    and the option keeps that unless the admin turns it off. Emby has three
    flags (IsHidden, IsHiddenRemotely and IsHiddenFromUnusedDevices) with other
    defaults, so Wizarr keeps the Emby defaults.
    """
    if server is None or server.server_type != "jellyfin":
        return {}
    return {"IsHidden": bool(server.hide_users_from_login)}


@register_media_client("jellyfin")
class JellyfinClient(RestApiMixin):
    """Wrapper around the Jellyfin REST API using credentials from Settings."""

    capabilities = ClientCapabilities(disable=True)

    @classmethod
    def check_connection(cls, url: str, token: str) -> tuple[bool, str]:
        from app.services.servers import check_jellyfin

        return check_jellyfin(url, token)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("url_key", "server_url")
        kwargs.setdefault("token_key", "api_key")
        super().__init__(*args, **kwargs)

    def _headers(self) -> dict[str, str]:
        """Return default headers for Jellyfin API requests."""
        return media_browser_auth_headers(self.token)

    def libraries(self) -> dict[str, str]:
        """Return mapping of library_id → library_name."""
        try:
            items = self.get("/Library/MediaFolders").json()["Items"]
            return {item["Id"]: item["Name"] for item in items}
        except Exception as exc:
            logging.warning("Jellyfin: failed to fetch libraries – %s", exc)
            return {}

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        """Scan available libraries on this Jellyfin server.

        Args:
            url: Optional server URL override
            token: Optional API token override

        Returns:
            dict: Library name -> library ID mapping
        """
        try:
            if url and token:
                response = requests.get(
                    f"{url.rstrip('/')}/Library/MediaFolders",
                    headers=media_browser_auth_headers(token),
                    timeout=10,
                )
                response.raise_for_status()
                items = response.json()["Items"]
            else:
                items = self.get("/Library/MediaFolders").json()["Items"]

            return {item["Name"]: item["Id"] for item in items}
        except Exception as exc:
            logging.warning("Jellyfin: failed to scan libraries – %s", exc)
            return {}

    def create_user(self, username: str, password: str) -> str:
        return self.post(
            "/Users/New", json={"Name": username, "Password": password}
        ).json()["Id"]

    def set_policy(self, user_id: str, policy: dict) -> None:
        self.post(f"/Users/{user_id}/Policy", json=policy)

    def delete_user(self, user_id: str) -> None:
        self.delete(f"/Users/{user_id}")

    def get_user(self, jf_id: str) -> dict:
        """Get user info in legacy format for backward compatibility."""
        details = self.get_user_details(jf_id)
        return {
            "Name": details.username,
            "Id": details.user_id,
            "Email": details.email,
            "Policy": {
                "IsAdministrator": details.is_admin,
                "EnableContentDownloading": details.allow_downloads,
                "EnableLiveTvAccess": details.allow_live_tv,
                "AllowCameraUpload": details.allow_camera_upload,
            },
            "Configuration": {},
        }

    def get_user_details(self, user_identifier: str | int) -> "MediaUserDetails":
        """Get detailed user information from database (no API calls)."""
        from app.services.media.user_details import MediaUserDetails, UserLibraryAccess

        jf_id = str(user_identifier)
        if not (
            user := User.query.filter_by(token=jf_id, server_id=self.server_id).first()
        ):
            raise ValueError(f"No user found with id {jf_id}")

        # Build library access from stored names
        library_access = None
        if library_names := user.get_accessible_libraries():
            libs_by_name = {
                lib.name: lib
                for lib in Library.query.filter(
                    Library.server_id == self.server_id, Library.name.in_(library_names)
                ).all()
            }
            library_access = [
                UserLibraryAccess(
                    library_id=lib.external_id
                    if (lib := libs_by_name.get(name))
                    else f"jf_{name}",
                    library_name=name,
                    has_access=True,
                )
                for name in library_names
            ]

        return MediaUserDetails(
            user_id=user.token,
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

    def update_user(self, jf_id: str, form: dict) -> dict | None:
        current = self.get_user(jf_id)

        for key, val in form.items():
            for section in ("Policy", "Configuration"):
                if key in current[section]:
                    target = current[section][key]
                    if isinstance(target, bool):
                        val = val == "True"
                    elif isinstance(target, int):
                        val = int(val) if isinstance(val, str | int) else 0
                    elif isinstance(target, list):
                        val = (
                            []
                            if val == ""
                            else (val.split(", ") if isinstance(val, str) else [])
                        )
                    current[section][key] = val

        return self.post(f"/Users/{jf_id}", json=current).json()

    def update_user_permissions(
        self, _user_identifier: str, _permissions: dict[str, bool]
    ) -> bool:
        """Update user permissions on Jellyfin.

        Args:
            _user_identifier: User's Jellyfin ID (external_id from database)
            _permissions: Dict with keys: allow_downloads, allow_live_tv, allow_camera_upload

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current policy
            raw_user = self.get(f"/Users/{_user_identifier}").json()
            if not raw_user:
                logging.error(f"Jellyfin: User {_user_identifier} not found")
                return False

            current_policy = raw_user.get("Policy", {})

            # Update permissions
            current_policy["EnableContentDownloading"] = _permissions.get(
                "allow_downloads", False
            )
            current_policy["EnableLiveTvAccess"] = _permissions.get(
                "allow_live_tv", False
            )
            # Jellyfin doesn't have a direct camera upload setting, but we keep the interface consistent
            # Store it in a comment field if needed in the future

            # Update policy
            response = self.post(
                f"/Users/{_user_identifier}/Policy", json=current_policy
            )
            success = response.status_code in {204, 200}

            if success:
                logging.info(
                    f"Successfully updated permissions for Jellyfin user {_user_identifier}"
                )
            return success

        except Exception as e:
            logging.error(
                f"Failed to update Jellyfin permissions for {_user_identifier}: {e}"
            )
            return False

    def update_user_libraries(
        self, _user_identifier: str, _library_names: list[str] | None
    ) -> bool:
        """Update user's library access on Jellyfin.

        Args:
            _user_identifier: User's Jellyfin ID (external_id from database)
            _library_names: List of library names to grant access to, or None for all libraries

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current policy
            raw_user = self.get(f"/Users/{_user_identifier}").json()
            if not raw_user:
                logging.error(f"Jellyfin: User {_user_identifier} not found")
                return False

            current_policy = raw_user.get("Policy", {})

            # Get library external IDs from database
            folder_ids = []
            if _library_names is not None:
                logging.info(f"JELLYFIN: Requested libraries: {_library_names}")
                libraries = (
                    Library.query.filter_by(server_id=self.server_id)
                    .filter(Library.name.in_(_library_names))
                    .all()
                )

                for lib in libraries:
                    folder_ids.append(lib.external_id)
                    logging.info(f"  ✓ {lib.name} -> {lib.external_id}")

                # Check for missing libraries
                found_names = {lib.name for lib in libraries}
                missing = set(_library_names) - found_names
                for name in missing:
                    logging.warning(
                        f"  ✗ Library '{name}' not found in database (scan libraries to fix)"
                    )

                logging.info(f"JELLYFIN: Converted to folder IDs: {folder_ids}")
            else:
                # None means all libraries - get all enabled libraries for this server
                libraries = Library.query.filter_by(
                    server_id=self.server_id, enabled=True
                ).all()
                folder_ids = [lib.external_id for lib in libraries]
                logging.info(f"JELLYFIN: Using all library IDs: {folder_ids}")

            # Update policy with library access
            current_policy["EnableAllFolders"] = _library_names is None
            current_policy["EnabledFolders"] = (
                folder_ids if _library_names is not None else []
            )

            # Update policy
            response = self.post(
                f"/Users/{_user_identifier}/Policy", json=current_policy
            )
            success = response.status_code in {204, 200}

            if success:
                logging.info(
                    f"Successfully updated library access for Jellyfin user {_user_identifier}"
                )
            return success

        except Exception as e:
            logging.error(
                f"Failed to update Jellyfin library access for {_user_identifier}: {e}"
            )
            return False

    def reset_password(self, user_identifier: str, new_password: str) -> bool:
        """Reset a Jellyfin user's password using the REST API.

        Args:
            user_identifier: Jellyfin user ID
            new_password: The new password to set

        Returns:
            bool: True if the operation succeeded, False otherwise
        """
        try:
            # Reuse the same contract as Emby: POST /Users/{id}/Password
            payload = {
                "NewPw": new_password,
                "CurrentPassword": "",
                "CurrentPw": "",
                "ResetPassword": False,
            }
            resp = self.post(f"/Users/{user_identifier}/Password", json=payload)
            success = resp.status_code in {200, 204}
            if success:
                logging.info(f"Password reset for Jellyfin user {user_identifier}")
            else:
                logging.warning(
                    f"Failed to reset Jellyfin password for {user_identifier}: HTTP {resp.status_code}"
                )
            return success
        except Exception as e:
            logging.error(
                f"Error resetting Jellyfin password for {user_identifier}: {e}"
            )
            return False

    def enable_user(self, user_id: str) -> bool:
        """Enable a user account on Jellyfin.

        Args:
            user_id: The user's Jellyfin ID

        Returns:
            bool: True if the user was successfully enabled, False otherwise
        """
        try:
            raw_user = self.get(f"/Users/{user_id}").json()
            if not raw_user:
                return False

            policy = raw_user.get("Policy", {})
            policy["IsDisabled"] = False

            response = self.post(f"/Users/{user_id}/Policy", json=policy)
            return response.status_code in {204, 200}
        except Exception as e:
            structlog.get_logger().error(f"Failed to enable Jellyfin user: {e}")
            return False

    def disable_user(self, user_id: str) -> bool:
        """Disable a user account on Jellyfin.

        Args:
            user_id: The user's Jellyfin ID

        Returns:
            bool: True if the user was successfully disabled, False otherwise
        """
        try:
            raw_user = self.get(f"/Users/{user_id}").json()
            if not raw_user:
                return False

            policy = raw_user.get("Policy", {})
            policy["IsDisabled"] = True

            response = self.post(f"/Users/{user_id}/Policy", json=policy)
            return response.status_code in {204, 200}
        except Exception as e:
            structlog.get_logger().error(f"Failed to disable Jellyfin user: {e}")
            return False

    def _get_server_users(self) -> list[User]:
        """Get all users for this server from database."""
        return User.query.filter(User.server_id == self.server_id).all()

    def _extract_jellyfin_permissions(self, jf_user: dict) -> dict[str, bool]:
        """Extract all permissions from a Jellyfin user object."""
        policy = jf_user.get("Policy", {}) or {}

        return {
            "is_admin": policy.get("IsAdministrator", False),
            "allow_downloads": policy.get("EnableContentDownloading", True),
            "allow_live_tv": policy.get("EnableLiveTvAccess", False),
            "allow_camera_upload": policy.get("AllowCameraUpload", False),
        }

    def _library_names_by_external_id(self) -> dict[str, str]:
        """Return {external_id: name} for this server's libraries in one query."""
        names: dict[str, str] = {}
        for external_id, name in (
            Library.query.with_entities(Library.external_id, Library.name)
            .filter(Library.server_id == self.server_id)
            .order_by(Library.id)
            .all()
        ):
            names.setdefault(str(external_id), name)
        return names

    def _get_user_library_access(
        self, jf_user: dict, library_names_by_id: dict[str, str] | None = None
    ) -> tuple[list[str] | None, bool]:
        """Extract library access: (library_names | None, has_full_access).

        Give ``library_names_by_id`` when you sync many users, so that the
        library rows are read only one time.
        """
        if (policy := jf_user.get("Policy", {}) or {}).get("EnableAllFolders", False):
            return None, True

        if not (enabled_folders := policy.get("EnabledFolders", []) or []):
            return None, True  # No restrictions = full access

        if library_names_by_id is None:
            library_names_by_id = self._library_names_by_external_id()

        # Map library IDs to names
        library_names = [
            name
            for lib_id in enabled_folders
            if (name := library_names_by_id.get(str(lib_id))) is not None
        ]
        return library_names, False

    def _sync_user_permissions(
        self,
        user: User,
        jf_user: dict,
        library_names_by_id: dict[str, str] | None = None,
    ) -> None:
        """Sync permissions and library access from Jellyfin to database user."""
        user.username = jf_user.get("Name", user.username)
        user.email = jf_user.get("Email", user.email)

        # Store permissions in SQL columns
        perms = self._extract_jellyfin_permissions(jf_user)
        user.is_admin = perms["is_admin"]
        user.allow_downloads = perms["allow_downloads"]
        user.allow_live_tv = perms["allow_live_tv"]
        user.allow_camera_upload = perms["allow_camera_upload"]

        # Store library access
        library_names, has_full_access = self._get_user_library_access(
            jf_user, library_names_by_id
        )
        user.set_accessible_libraries(library_names if not has_full_access else None)

    def list_users(self) -> list[User]:
        """Sync users from Jellyfin to database with all permissions and library access."""
        if not self.server_id:
            return []

        # The remote call comes first, before any DB write, so the SQLite
        # write lock is not held while we wait for the server.
        try:
            raw_users = self.get("/Users").json()
        except Exception as exc:
            logging.warning("Jellyfin: failed to list users – %s", exc)
            return self._get_server_users()

        jf_users_by_id = {u["Id"]: u for u in raw_users}

        known_users = self._get_server_users()
        if self._skip_prune_on_empty_remote(not jf_users_by_id, known_users):
            return known_users

        # Read the library rows one time for all users.
        library_names_by_id = self._library_names_by_external_id()

        # Remove users no longer in Jellyfin, add new users. Use the rows that
        # are already loaded, not one query for each remote user.
        synced_users: list[User] = []
        for db_user in known_users:
            if db_user.token in jf_users_by_id:
                synced_users.append(db_user)
            else:
                db.session.delete(db_user)

        known_tokens = {user.token for user in synced_users}
        for jf_id, jf_user in jf_users_by_id.items():
            if jf_id not in known_tokens:
                new_user = User(
                    token=jf_id,
                    username=jf_user.get("Name", "jf-user"),
                    email="empty",
                    code="empty",
                    server_id=self.server_id,
                )
                db.session.add(new_user)
                synced_users.append(new_user)

        # Sync all permissions and library access
        for user in synced_users:
            self._sync_user_permissions(
                user, jf_users_by_id[user.token], library_names_by_id
            )

        try:
            db.session.commit()
            logging.info(f"Synced {len(jf_users_by_id)} Jellyfin users to database")
        except Exception as e:
            logging.error(f"Failed to sync Jellyfin user metadata: {e}")
            db.session.rollback()

        return self._get_server_users()

    def _password_for_db(self, password: str) -> str:
        return password

    @staticmethod
    def _folder_name_to_id(name: str, cache: dict[str, str]) -> str | None:
        if name in cache.values():
            return name
        return cache.get(name)

    def _set_specific_folders(self, user_id: str, names: list[str]) -> None:
        log = structlog.get_logger(__name__)
        items = self.get("/Library/MediaFolders").json()["Items"]
        mapping = {item["Name"]: item["Id"] for item in items}
        # Also map IDs directly so callers may pass either a name or an Id.
        mapping.update({v: v for v in mapping.values()})

        log.debug("jellyfin._set_specific_folders", user_id=user_id, requested=names)

        folder_ids = [self._folder_name_to_id(n, mapping) for n in names]
        folder_ids = [fid for fid in folder_ids if fid]

        if names and not folder_ids:
            log.warning(
                "jellyfin._set_specific_folders.no_libraries_resolved",
                user_id=user_id,
                requested=names,
                hint="No requested libraries could be mapped to a Jellyfin folder Id. "
                "Re-scan libraries on the server settings page to refresh external IDs.",
            )
            # Restrict to nothing rather than silently granting access to all libraries.
            policy_patch = {
                "EnableAllFolders": False,
                "EnabledFolders": [],
            }
        else:
            policy_patch = {
                "EnableAllFolders": not folder_ids,
                "EnabledFolders": folder_ids,
            }

        log.debug(
            "jellyfin._set_specific_folders.applying",
            user_id=user_id,
            enable_all=policy_patch["EnableAllFolders"],
            folder_ids=folder_ids,
        )

        current = self.get(f"/Users/{user_id}").json()["Policy"]
        current.update(policy_patch)
        self.set_policy(user_id, current)

    # --- public sign-up ---------------------------------------------

    def _do_join(
        self,
        username: str,
        password: str,
        confirm: str,
        email: str,
        code: str,
    ) -> tuple[bool, str]:
        if not EMAIL_RE.fullmatch(email):
            return False, "Invalid e-mail address."
        if not 8 <= len(password) <= 128:
            return False, "Password must be 8–128 characters."
        if password != confirm:
            return False, "Passwords do not match."

        ok, msg = is_invite_valid(code)
        if not ok:
            return False, msg

        server_id = getattr(self, "server_id", None)
        existing = User.query.filter(
            or_(User.username == username, User.email == email),
            User.server_id == server_id,
        ).first()
        if existing:
            return False, "User or e-mail already exists."

        try:
            user_id = self.create_user(username, password)
            inv = Invitation.query.filter_by(code=code).first()

            if inv and inv.libraries:
                sections = [
                    lib.external_id
                    for lib in inv.libraries
                    if lib.server_id == server_id
                ]
                logging.info(
                    f"JELLYFIN: Using invitation libraries for user {username}: {sections}"
                )
            else:
                sections = [
                    lib.external_id
                    for lib in Library.query.filter_by(
                        enabled=True, server_id=server_id
                    ).all()
                ]
                logging.info(
                    f"JELLYFIN: No specific libraries, using all enabled: {sections}"
                )

            self._set_specific_folders(user_id, sections)

            # Use universal columns
            allow_downloads = bool(getattr(inv, "allow_downloads", False))
            allow_live_tv = bool(getattr(inv, "allow_live_tv", False))

            if server_id:
                from app.models import MediaServer

                current_server = db.session.get(MediaServer, server_id)
                if current_server:
                    if not allow_downloads:
                        allow_downloads = bool(
                            getattr(current_server, "allow_downloads", False)
                        )
                    if not allow_live_tv:
                        allow_live_tv = bool(
                            getattr(current_server, "allow_live_tv", False)
                        )

            current_policy = self.get(f"/Users/{user_id}").json().get("Policy", {})
            current_policy["EnableContentDownloading"] = allow_downloads
            current_policy["EnableLiveTvAccess"] = allow_live_tv
            current_policy.update(
                login_screen_policy(getattr(self, "server_row", None))
            )

            # Apply Jellyfin max active sessions setting
            max_sessions = getattr(inv, "max_active_sessions", None)
            if max_sessions is not None:
                current_policy["MaxActiveSessions"] = max_sessions

            self.set_policy(user_id, current_policy)

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
                    "server_id": server_id,
                }
            )
            db.session.commit()

            return True, ""

        except Exception:
            logging.error("Jellyfin join error", exc_info=True)
            db.session.rollback()
            return False, "An unexpected error occurred."

    def _get_artwork_urls(
        self, item_id: str, media_type: str = "", series_id: str | None = None
    ) -> dict[str, str | None]:
        if not item_id:
            return {
                "artwork_url": None,
                "fallback_artwork_url": None,
                "thumbnail_url": None,
            }

        poster_item_id = (
            series_id if (media_type == "episode" and series_id) else item_id
        )

        # Use direct Jellyfin image endpoints instead of fetching remote metadata
        # This avoids slow RemoteImages API calls that often timeout
        auth_param = f"&api_key={self.token}" if self.token else ""

        # Primary artwork for the item (poster), resized for the card
        artwork_url = (
            f"{self.url}/Items/{poster_item_id}/Images/Primary"
            f"?{NOW_PLAYING_POSTER_PARAMS}{auth_param}"
        )
        fallback_artwork_url = artwork_url

        # For episodes/series, also try to get a backdrop image as thumbnail
        # But use Primary as fallback to avoid another potentially slow call.
        # The card shows the backdrop blurred, so we ask for a small image.
        thumbnail_url = (
            f"{self.url}/Items/{poster_item_id}/Images/Backdrop"
            f"?{NOW_PLAYING_BACKDROP_PARAMS}{auth_param}"
        )

        return {
            "artwork_url": artwork_url,
            "fallback_artwork_url": fallback_artwork_url,
            "thumbnail_url": thumbnail_url,
        }

    def get_movie_posters(self, limit: int = 10) -> list[str]:
        """Get movie poster URLs for background display."""
        poster_urls = []
        try:
            # Get recent movies from all libraries. Recursive is required: without
            # it /Items only returns the library folders at the root, so this came
            # back empty and the cinema background silently showed nothing. Safe to
            # enable now only because the poster URLs below go through the image
            # proxy; enabling it while the raw api_key URL was returned would have
            # turned the latent /cinema-posters leak into an active one.
            response = self.get(
                "/Items",
                params={
                    "IncludeItemTypes": "Movie",
                    "SortBy": "DateCreated",
                    "SortOrder": "Descending",
                    "Limit": limit * 2,  # Get more than needed as fallback
                    "Fields": "PrimaryImageAspectRatio",
                    "HasPrimaryImage": True,
                    "Recursive": True,
                },
            ).json()

            if response.get("Items"):
                for item in response["Items"]:
                    if len(poster_urls) >= limit:
                        break

                    item_id = item.get("Id")
                    if item_id:
                        # Build the poster URL and route it through the image
                        # proxy. The api_key is deliberately kept out of the URL;
                        # the proxy re-attaches it as a header server-side (see
                        # ImageProxyService.get_server_headers), so the admin
                        # token is never exposed to the client. We ask for a
                        # resized image: the full-size poster is much larger
                        # than the join page shows.
                        poster_url = (
                            f"{self.url}/Items/{item_id}/Images/Primary"
                            f"?{POSTER_IMAGE_PARAMS}"
                        )
                        poster_urls.append(self.generate_image_proxy_url(poster_url))

        except Exception as e:
            import logging

            logging.warning(f"Failed to fetch movie posters from Jellyfin: {e}")

        return poster_urls[:limit]

    def now_playing(self) -> list[dict]:
        """Return the active sessions on this server.

        Raises on HTTP, connection and timeout errors, and when the session
        list is not valid JSON. Then a caller can tell a failed poll from a
        server with no sessions. Returns [] only when the server reports no
        active sessions.
        """
        sessions = self.get("/Sessions").json()
        if not isinstance(sessions, list):
            raise ValueError(
                f"{self.__class__.__name__} returned an invalid session list"
            )

        now_playing_sessions = []
        for session in sessions:
            try:
                session_info = self._now_playing_entry(session)
            except Exception as exc:
                # One bad session must not hide the other sessions.
                logging.warning(
                    f"Failed to read a {self.__class__.__name__} session: {exc}"
                )
                continue
            if session_info is not None:
                now_playing_sessions.append(session_info)

        return now_playing_sessions

    @staticmethod
    def _play_method(session: dict) -> str | None:
        """Return the play method of a /Sessions entry.

        Jellyfin and Emby put PlayMethod in PlayState. The top-level key is
        a fallback.
        """
        play_state = session.get("PlayState") or {}
        return play_state.get("PlayMethod") or session.get("PlayMethod")

    @classmethod
    def _playback_mode(cls, session: dict) -> tuple[bool, bool]:
        """Return (is_transcoding, direct_play) for a /Sessions entry.

        The server also sends TranscodingInfo for a remux, where it copies
        the video and the audio into a new container. A remux is a direct
        stream, not a transcode. The Jellyfin dashboard uses the same rules.
        """
        play_method = cls._play_method(session)
        if play_method == "DirectPlay":
            return False, True
        if play_method == "DirectStream":
            return False, False
        transcode = session.get("TranscodingInfo")
        if transcode:
            video_direct = transcode.get("IsVideoDirect") or not transcode.get(
                "VideoCodec"
            )
            return not (video_direct and transcode.get("IsAudioDirect")), False
        is_transcoding = play_method == "Transcode"
        return is_transcoding, not is_transcoding

    def _now_playing_entry(self, session: dict) -> dict | None:
        """Convert one /Sessions entry to a now-playing dict."""
        if session.get("NowPlayingItem") is None:
            return None

        now_playing_item = session["NowPlayingItem"]
        play_state = session.get("PlayState", {})

        progress = 0.0
        if play_state.get("PositionTicks") and now_playing_item.get("RunTimeTicks"):
            progress = max(
                0.0,
                min(
                    1.0,
                    play_state["PositionTicks"] / now_playing_item["RunTimeTicks"],
                ),
            )

        media_type = now_playing_item.get("Type", "unknown").lower()

        # Extract series info for episodes (both for formatting and separate fields)
        series_name = None
        season_num = None
        episode_num = None
        media_title = now_playing_item.get("Name", "Unknown")

        if media_type == "episode":
            series_name = now_playing_item.get("SeriesName")
            season_num = now_playing_item.get("ParentIndexNumber")
            episode_num = now_playing_item.get("IndexNumber")

            # Format title for display
            if series_name:
                media_title = f"{series_name}"
                if season_num and episode_num:
                    media_title += f" S{season_num:02d}E{episode_num:02d}"
                media_title += f" - {now_playing_item.get('Name', '')}"

        state = "stopped"
        if play_state.get("IsPaused"):
            state = "paused"
        elif play_state.get("PositionTicks") is not None:
            state = "playing"

        # Extract user and session info
        user_info = session.get("UserName", "Unknown User")
        user_id = session.get("UserId")
        session_id = session.get("Id", "")

        # Extract device and platform info
        ip_address = session.get("RemoteEndPoint")
        platform = session.get("DeviceType")
        player_version = session.get("ApplicationVersion")

        item_id = now_playing_item.get("Id")
        series_id = now_playing_item.get("SeriesId")
        artwork_info = self._get_artwork_urls(item_id, media_type, series_id)

        is_transcoding, direct_play = self._playback_mode(session)
        transcoding_info: dict[str, Any] = {
            "is_transcoding": is_transcoding,
            "video_codec": None,
            "audio_codec": None,
            "container": None,
            "video_resolution": None,
            "transcoding_speed": None,
            "direct_play": direct_play,
        }

        if session.get("TranscodingInfo"):
            transcode_info = session["TranscodingInfo"]
            transcoding_info["video_codec"] = transcode_info.get("VideoCodec")
            transcoding_info["audio_codec"] = transcode_info.get("AudioCodec")
            transcoding_info["container"] = transcode_info.get("Container")
            transcoding_info["transcoding_speed"] = transcode_info.get(
                "TranscodingFramerate"
            )

        if now_playing_item.get("MediaStreams"):
            for stream in now_playing_item["MediaStreams"]:
                if (
                    stream.get("Type") == "Video"
                    and not transcoding_info["video_codec"]
                ):
                    transcoding_info["video_codec"] = stream.get("Codec")
                    transcoding_info["video_resolution"] = (
                        stream.get("DisplayTitle")
                        or f"{stream.get('Width', '?')}x{stream.get('Height', '?')}"
                    )
                elif (
                    stream.get("Type") == "Audio"
                    and not transcoding_info["audio_codec"]
                ):
                    transcoding_info["audio_codec"] = stream.get("Codec")

        if not transcoding_info["container"]:
            transcoding_info["container"] = now_playing_item.get("Container")

        return {
            # Required fields
            "user_name": user_info,
            "media_title": media_title,
            "session_id": session_id,
            # User info
            "user_id": user_id,
            # Media info
            "media_type": media_type,
            "media_id": item_id,
            "series_name": series_name,
            "season_number": season_num,
            "episode_number": episode_num,
            # Playback info
            "progress": progress,
            "state": state,
            "position_ms": play_state.get("PositionTicks", 0) // 10000,
            "duration_ms": now_playing_item.get("RunTimeTicks", 0) // 10000,
            # Device info
            "client": session.get("Client", ""),
            "device_name": session.get("DeviceName", ""),
            "ip_address": ip_address,
            "platform": platform,
            "player_version": player_version,
            # Artwork
            "artwork_url": artwork_info["artwork_url"],
            "fallback_artwork_url": artwork_info["fallback_artwork_url"],
            "thumbnail_url": artwork_info["thumbnail_url"],
            # Transcoding
            "transcoding_info": transcoding_info,
            # Metadata
            "metadata": {
                "jellyfin_session_id": session_id,
                "jellyfin_item_id": item_id,
                "jellyfin_series_id": series_id,
                "play_method": self._play_method(session),
            },
        }

    def get_recent_items(
        self,
        library_id: str | None = None,
        limit: int = 10,
        library_names: Collection[str] | None = None,
    ) -> list[dict]:
        """Get the newest items of the selected Jellyfin libraries.

        Without ``library_names``, one request gets the newest items of all
        libraries. With names, each selected library gives its newest *limit*
        items, and the result is the newest *limit* items of all of them.
        """
        if library_id or library_names is None:
            return self._recent_items_in(library_id, limit)

        items: list[dict] = []
        for folder_id in self._library_folder_ids(library_names):
            items.extend(self._recent_items_in(folder_id, limit))
        return newest_first(items, limit)

    def _library_folder_ids(self, library_names: Collection[str]) -> list[str]:
        """Return the IDs of the library folders that have the given names."""
        try:
            folders = self.get("/Library/MediaFolders").json()["Items"]
        except Exception as exc:
            logging.warning("Jellyfin: failed to fetch libraries – %s", exc)
            return []
        return [
            folder["Id"]
            for folder in folders
            if library_name_selected(folder.get("Name", ""), library_names)
        ]

    def _recent_items_in(self, parent_id: str | None, limit: int) -> list[dict]:
        """Get the newest items in one folder, or in all libraries if no folder."""
        try:
            # Use the regular Items endpoint with proper sorting for recently added content
            # Only include items that have proper vertical poster images (exclude Episodes which use horizontal thumbnails)
            params = {
                "SortBy": "DateCreated",
                "SortOrder": "Descending",
                "Limit": limit * 2,  # Request more items since we'll filter some out
                "Fields": "Overview,Genres,DateCreated,ProductionYear",
                "ImageTypeLimit": 1,
                "EnableImageTypes": "Primary",
                "Recursive": True,
                "IncludeItemTypes": "Movie,Series,MusicAlbum",  # Only types with vertical posters
            }

            if parent_id:
                params["ParentId"] = parent_id

            response = self.get("/Items", params=params)
            response_data = response.json()

            if not isinstance(response_data, dict) or "Items" not in response_data:
                return []

            items = []
            for item in response_data["Items"]:
                # Stop if we've reached the limit
                if len(items) >= limit:
                    break

                # Only show items that have actual poster images (Primary for movies/series)
                thumb_url = None
                image_tags = item.get("ImageTags", {})

                # Use Primary image for vertical posters
                if image_tags.get("Primary"):
                    thumb_url = f"{self.url}/Items/{item['Id']}/Images/Primary?maxHeight=400&quality=90"
                    if self.token:
                        thumb_url += f"&api_key={self.token}"

                if thumb_url:
                    # Generate secure proxy URL with opaque token
                    thumb_url = self.generate_image_proxy_url(thumb_url)

                    # Only add items that have images
                    items.append(
                        {
                            "title": item.get("Name", "Unknown"),
                            "year": item.get("ProductionYear"),
                            "thumb": thumb_url,
                            "type": item.get("Type", "").lower(),
                            "added_at": item.get("DateCreated"),
                        }
                    )

            return items

        except Exception:
            return []

    def statistics(self):
        try:
            stats = {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
            }

            sessions = self.get("/Sessions").json()
            active_sessions = [s for s in sessions if s.get("NowPlayingItem")]
            transcoding_sessions = [s for s in sessions if s.get("TranscodingInfo")]

            try:
                users = self.get("/Users").json()
                stats["user_stats"] = {
                    "total_users": len(users),
                    "active_sessions": len(active_sessions),
                }
            except Exception as e:
                logging.error(f"Failed to get Jellyfin user stats: {e}")
                stats["user_stats"] = {"total_users": 0, "active_sessions": 0}

            try:
                system_info = self.get("/System/Info").json()
                stats["server_stats"] = {
                    "version": system_info.get("Version", "Unknown"),
                    "transcoding_sessions": len(transcoding_sessions),
                }
            except Exception as e:
                logging.error(f"Failed to get Jellyfin server stats: {e}")
                stats["server_stats"] = {}

            return stats

        except Exception as e:
            logging.error(f"Failed to get Jellyfin statistics: {e}")
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
            # Count existing users in database for this server instead of API call
            from app.models import MediaServer, User

            if hasattr(self, "server_id") and self.server_id:
                count = User.query.filter_by(server_id=self.server_id).count()
            else:
                # Fallback for legacy settings: find MediaServer for this server type
                server_type = getattr(self, "_server_type", "jellyfin")
                servers = MediaServer.query.filter_by(server_type=server_type).all()
                if servers:
                    server_ids = [s.id for s in servers]
                    count = User.query.filter(User.server_id.in_(server_ids)).count()
                else:
                    # Ultimate fallback: API call
                    try:
                        users = self.get("/Users").json()
                        count = len(users) if isinstance(users, list) else 0
                    except Exception as api_error:
                        logging.warning(
                            f"{self.__class__.__name__} API fallback failed: {api_error}"
                        )
                        count = 0
            return count
        except Exception as e:
            logging.error(
                f"Failed to get {self.__class__.__name__} user count from database: {e}"
            )
            return 0

    def get_server_info(self) -> dict:
        """Get lightweight server information without triggering user sync."""
        try:
            # Get basic server info and session counts without calling list_users()
            sessions = []
            transcoding_sessions = []

            try:
                sessions = self.get("/Sessions").json()
                active_sessions = [s for s in sessions if s.get("NowPlayingItem")]
                transcoding_sessions = [s for s in sessions if s.get("TranscodingInfo")]
            except Exception as e:
                logging.warning(
                    f"Failed to get {self.__class__.__name__} session info: {e}"
                )
                active_sessions = []
                transcoding_sessions = []

            try:
                system_info = self.get("/System/Info").json()
                version = system_info.get("Version", "Unknown")
            except Exception as e:
                logging.warning(
                    f"Failed to get {self.__class__.__name__} system info: {e}"
                )
                version = "Unknown"

            return {
                "version": version,
                "transcoding_sessions": len(transcoding_sessions),
                "active_sessions": len(active_sessions),
            }
        except Exception as e:
            logging.error(f"Failed to get {self.__class__.__name__} server info: {e}")
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
            logging.error(
                f"Failed to get {self.__class__.__name__} readonly statistics: {e}"
            )
            return {
                "user_stats": {"total_users": 0, "active_sessions": 0},
                "server_stats": {"version": "Unknown", "transcoding_sessions": 0},
                "library_stats": {},
                "content_stats": {},
                "error": str(e),
            }


# ─── Admin-side helpers – mirror the Plex API we already exposed ──────────
