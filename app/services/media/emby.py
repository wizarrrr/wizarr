import logging
import re
from typing import TYPE_CHECKING

import requests
from sqlalchemy import or_

from app.models import Invitation, MediaServer, User

from .client_base import register_media_client
from .jellyfin import JellyfinClient

if TYPE_CHECKING:
    pass

# Reuse the same email regex as jellyfin
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")


@register_media_client("emby")
class EmbyClient(JellyfinClient):
    """Wrapper around the Emby REST API using credentials from Settings."""

    def libraries(self) -> dict[str, str]:
        """Return mapping of library GUIDs to names."""
        try:
            items = self.get("/Library/MediaFolders").json()["Items"]
            return {item["Guid"]: item["Name"] for item in items}
        except Exception as exc:
            logging.warning("Emby: failed to fetch libraries – %s", exc)
            return {}

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        """Scan available libraries on this Emby server.

        Args:
            url: Optional server URL override
            token: Optional API token override

        Returns:
            dict: Library name -> library GUID mapping
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

            return {item["Name"]: item["Guid"] for item in items}
        except Exception as exc:
            logging.warning("Emby: failed to scan libraries – %s", exc)
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

    def _password_for_db(self, password: str) -> str:
        """Return placeholder password for local DB."""
        return "emby-user"

    def _set_specific_folders(self, user_id: str, names: list[str]):
        """Set library access for a user and ensure playback permissions."""
        items = self.get("/Library/MediaFolders").json()["Items"]
        mapping = {i["Name"]: i["Guid"] for i in items}

        # Debug logging
        logging.info(f"EMBY: _set_specific_folders called with names: {names}")
        logging.info(f"EMBY: mapping: {mapping}")

        folder_ids = [self._folder_name_to_id(n, mapping) for n in names]
        folder_ids = [fid for fid in folder_ids if fid]

        logging.info(f"EMBY: folder_ids after mapping: {folder_ids}")

        policy_patch = {
            "EnableAllFolders": not folder_ids,
            "EnabledFolders": folder_ids,
            "EnableMediaPlayback": True,
            "EnableAudioPlaybackTranscoding": True,
            "EnableVideoPlaybackTranscoding": True,
            "EnablePlaybackRemuxing": True,
            "EnableRemoteAccess": True,
        }

        logging.info(f"EMBY: Setting policy patch for user {user_id}: {policy_patch}")

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

        current_server = MediaServer.query.get(server_id)
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
                f"Failed to set Emby download/live TV/mobile uploads permissions for user {username}: {str(e)}"
            )
            # Don't fail the join process for this

        return success, message
