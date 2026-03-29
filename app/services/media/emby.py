import logging
import re
from typing import TYPE_CHECKING

import requests
import structlog
from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, MediaServer, User

from .client_base import register_media_client
from .jellyfin import JellyfinClient

if TYPE_CHECKING:
    pass

# Reuse the same email regex as jellyfin
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")

log = structlog.get_logger(__name__)


@register_media_client("emby")
class EmbyClient(JellyfinClient):
    """Wrapper around the Emby REST API using credentials from Settings."""

    def libraries(self) -> dict[str, str]:
        """Return mapping of library Id to names.

        Uses ``Id`` (not ``Guid``) so that ``Library.external_id`` stores the
        value that Emby's ``EnabledFolders`` policy field actually expects.
        """
        try:
            items = self.get("/Library/MediaFolders").json()["Items"]
            return {item["Id"]: item["Name"] for item in items}
        except Exception as exc:
            log.warning("emby.libraries.failed", error=str(exc))
            return {}

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        """Scan available libraries on this Emby server.

        Args:
            url: Optional server URL override
            token: Optional API token override

        Returns:
            dict: Library name -> library Id mapping (uses ``Id``, not ``Guid``)
        """
        try:
            if url and token:
                headers = {"X-Emby-Token": token}
                response = requests.get(
                    f"{url.rstrip('/')}/Library/MediaFolders",
                    headers=headers,
                    timeout=10,
                )
                response.raise_for_status()
                items = response.json()["Items"]
            else:
                items = self.get("/Library/MediaFolders").json()["Items"]

            return {item["Name"]: item["Id"] for item in items}
        except Exception as exc:
            log.warning("emby.scan_libraries.failed", error=str(exc))
            return {}

    def statistics(self):
        """Return essential Emby server statistics for the dashboard.

        Only collects data actually used by the UI:
        - Server version for health card
        - Active sessions count for health card
        - Transcoding sessions count for health card
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

            # Get sessions once - used for both user and server stats
            sessions = self.get("/Sessions").json()
            active_sessions = [s for s in sessions if s.get("NowPlayingItem")]
            transcoding_sessions = [s for s in sessions if s.get("TranscodingInfo")]

            # User statistics - only what's displayed in UI
            try:
                users = self.get("/Users").json()
                stats["user_stats"] = {
                    "total_users": len(users),
                    "active_sessions": len(active_sessions),
                }
            except Exception as e:
                logging.error(f"Failed to get Emby user stats: {e}")
                stats["user_stats"] = {"total_users": 0, "active_sessions": 0}

            # Server statistics - only version and transcoding count
            try:
                system_info = self.get("/System/Info").json()
                stats["server_stats"] = {
                    "version": system_info.get("Version", "Unknown"),
                    "transcoding_sessions": len(transcoding_sessions),
                }
            except Exception as e:
                logging.error(f"Failed to get Emby server stats: {e}")
                stats["server_stats"] = {}

            return stats

        except Exception as e:
            logging.error(f"Failed to get Emby statistics: {e}")
            return {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
                "error": str(e),
            }

    def get_movie_posters(self, limit: int = 10) -> list[str]:
        """Get movie poster URLs for background display."""
        poster_urls = []
        try:
            # Get recent movies from all libraries (Emby API is similar to Jellyfin)
            response = self.get(
                "/Items",
                params={
                    "IncludeItemTypes": "Movie",
                    "SortBy": "DateCreated",
                    "SortOrder": "Descending",
                    "Limit": limit * 2,  # Get more than needed as fallback
                    "Fields": "PrimaryImageAspectRatio",
                    "HasPrimaryImage": True,
                },
            ).json()

            if response.get("Items"):
                for item in response["Items"]:
                    if len(poster_urls) >= limit:
                        break

                    item_id = item.get("Id")
                    if item_id:
                        # Build poster URL for Emby
                        poster_url = f"{self.url}/Items/{item_id}/Images/Primary"
                        if self.token:
                            poster_url += f"?api_key={self.token}"
                        poster_urls.append(poster_url)

        except Exception as e:
            import logging

            logging.warning(f"Failed to fetch movie posters from Emby: {e}")

        return poster_urls[:limit]

    def create_user(self, username: str, password: str) -> str:
        """Create user and set password."""
        # Step 1: Create user without password
        user = self.post("/Users/New", json={"Name": username}).json()
        user_id = user["Id"]

        # Step 2: Set password
        try:
            logging.info("Setting password for user %s (ID: %s)", username, user_id)
            password_response = self.post(
                f"/Users/{user_id}/Password",
                json={
                    "NewPw": password,
                    "CurrentPw": "",  # No current password for new users
                    "ResetPassword": False,  # Don't reset password
                },
            )
            logging.info("Password set response: %s", password_response.status_code)
        except Exception as e:
            logging.error("Failed to set password for user %s: %s", username, e)
            # Continue with user creation even if password setting fails

        return user_id

    def _password_for_db(self, _password: str) -> str:
        """Return placeholder password for local DB."""
        return "emby-user"

    def _set_specific_folders(self, user_id: str, names: list[str]) -> None:
        """Set library access for a user and ensure playback permissions.

        Builds a mapping of ``{Name: Id, Id: Id}`` so that lookups succeed
        whether ``names`` contains library names or already-resolved Ids.
        """
        items = self.get("/Library/MediaFolders").json()["Items"]
        # Primary mapping: Name -> Id
        mapping: dict[str, str] = {i["Name"]: i["Id"] for i in items}
        # Also allow Id passthrough and Guid -> Id for backwards compatibility
        mapping.update({i["Id"]: i["Id"] for i in items})
        mapping.update({i["Guid"]: i["Id"] for i in items if "Guid" in i})

        log.debug("emby._set_specific_folders", user_id=user_id, requested=names)

        folder_ids = [self._folder_name_to_id(n, mapping) for n in names]
        folder_ids = [fid for fid in folder_ids if fid]

        if names and not folder_ids:
            log.warning(
                "emby._set_specific_folders.no_libraries_resolved",
                user_id=user_id,
                requested=names,
                hint="No requested libraries could be mapped to an Emby folder Id. "
                "Re-scan libraries on the server settings page to refresh external IDs.",
            )
            # Restrict to nothing rather than silently granting everything.
            policy_patch = {
                "EnableAllFolders": False,
                "EnabledFolders": [],
                "EnableMediaPlayback": True,
                "EnableAudioPlaybackTranscoding": True,
                "EnableVideoPlaybackTranscoding": True,
                "EnablePlaybackRemuxing": True,
                "EnableRemoteAccess": True,
            }
        else:
            policy_patch = {
                "EnableAllFolders": not folder_ids,
                "EnabledFolders": folder_ids,
                "EnableMediaPlayback": True,
                "EnableAudioPlaybackTranscoding": True,
                "EnableVideoPlaybackTranscoding": True,
                "EnablePlaybackRemuxing": True,
                "EnableRemoteAccess": True,
            }

        log.debug(
            "emby._set_specific_folders.applying",
            user_id=user_id,
            enable_all=policy_patch["EnableAllFolders"],
            folder_ids=folder_ids,
        )

        current = self.get(f"/Users/{user_id}").json()["Policy"]
        current.update(policy_patch)
        self.set_policy(user_id, current)

    def join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
        """Override join method to handle universal download and live TV settings."""
        # Call the parent join method first
        success, message = super().join(username, password, confirm, email, code)

        if not success:
            return success, message

        # Get the invitation and server information
        inv = Invitation.query.filter_by(code=code).first()
        if not inv:
            return False, "Invalid invitation code."

        server_id = getattr(self, "server_id", None)
        if not server_id:
            return success, message

        current_server = db.session.get(MediaServer, server_id)
        if not current_server:
            return success, message

        # Get the user that was just created
        user = User.query.filter(
            or_(User.username == username, User.email == email),
            User.server_id == server_id,
        ).first()

        if not user:
            return success, message

        # Determine download, live TV, and mobile uploads settings using universal columns
        allow_downloads = bool(getattr(inv, "allow_downloads", False))
        allow_live_tv = bool(getattr(inv, "allow_live_tv", False))
        allow_mobile_uploads = bool(getattr(inv, "allow_mobile_uploads", False))

        # Fall back to server defaults if not set on invitation
        if not allow_downloads:
            allow_downloads = bool(getattr(current_server, "allow_downloads", False))
        if not allow_live_tv:
            allow_live_tv = bool(getattr(current_server, "allow_live_tv", False))
        if not allow_mobile_uploads:
            allow_mobile_uploads = bool(
                getattr(current_server, "allow_mobile_uploads", False)
            )

        # Update the user policy with download, live TV, and mobile uploads settings
        try:
            current_policy = self.get(f"/Users/{user.token}").json().get("Policy", {})
            current_policy["EnableContentDownloading"] = allow_downloads
            current_policy["EnableLiveTvAccess"] = allow_live_tv
            current_policy["AllowCameraUpload"] = allow_mobile_uploads
            self.set_policy(user.token, current_policy)
        except Exception as e:
            logging.error(
                f"Failed to set Emby download/live TV/mobile uploads permissions for user {username}: {e!s}"
            )
            # Don't fail the join process for this

        return success, message
