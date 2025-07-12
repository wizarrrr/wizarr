import logging
import re

from .jellyfin import JellyfinClient
from .client_base import register_media_client

# Reuse the same email regex as jellyfin
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")


@register_media_client("emby")
class EmbyClient(JellyfinClient):
    """Wrapper around the Emby REST API using credentials from Settings."""

    def libraries(self) -> dict[str, str]:
        """Return mapping of library GUIDs to names."""
        return {
            item["Guid"]: item["Name"]
            for item in self.get("/Library/MediaFolders").json()["Items"]
        }

    def scan_libraries(self, url: str = None, token: str = None) -> dict[str, str]:
        """Scan available libraries on this Emby server.
        
        Args:
            url: Optional server URL override
            token: Optional API token override
            
        Returns:
            dict: Library name -> library GUID mapping
        """
        import requests
        
        if url and token:
            # Use override credentials for scanning
            headers = {"X-Emby-Token": token}
            response = requests.get(
                f"{url.rstrip('/')}/Library/MediaFolders",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            items = response.json()["Items"]
        else:
            # Use saved credentials
            items = self.get("/Library/MediaFolders").json()["Items"]
        
        return {item["Name"]: item["Guid"] for item in items}

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
                "content_stats": {}
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
                    "active_sessions": len(active_sessions)
                }
            except Exception as e:
                logging.error(f"Failed to get Emby user stats: {e}")
                stats["user_stats"] = {
                    "total_users": 0,
                    "active_sessions": 0
                }
            
            # Server statistics - only version and transcoding count
            try:
                system_info = self.get("/System/Info").json()
                stats["server_stats"] = {
                    "version": system_info.get("Version", "Unknown"),
                    "transcoding_sessions": len(transcoding_sessions)
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
                "error": str(e)
            }

    def create_user(self, username: str, password: str) -> str:
        """Create user and set password"""
        # Step 1: Create user without password
        user = self.post("/Users/New", json={"Name": username}).json()
        user_id = user["Id"]
        
        # Step 2: Set password
        try:
            logging.info(f"Setting password for user {username} (ID: {user_id})")
            password_response = self.post(
                f"/Users/{user_id}/Password",
                json={
                    "NewPw": password,
                    "CurrentPw": "",  # No current password for new users
                    "ResetPassword": False  # Important! Don't reset password
                }
            )
            logging.info(f"Password set response: {password_response.status_code}")
        except Exception as e:
            logging.error(f"Failed to set password for user {username}: {str(e)}")
            # Continue with user creation even if password setting fails
            # as we may need to debug further
        
        return user_id
        

    def _password_for_db(self, password: str) -> str:
        """Return placeholder password for local DB."""
        return "emby-user"

    def _set_specific_folders(self, user_id: str, names: list[str]):
        """Set library access for a user and ensure playback permissions."""
        items = self.get("/Library/MediaFolders").json()["Items"]
        mapping = {i["Name"]: i["Guid"] for i in items}
        
        print(mapping)

        folder_ids = [self._folder_name_to_id(n, mapping) for n in names]
        folder_ids = [fid for fid in folder_ids if fid]

        policy_patch = {
            "EnableAllFolders": not folder_ids,
            "EnabledFolders": folder_ids,
            "EnableMediaPlayback": True,
            "EnableAudioPlaybackTranscoding": True,
            "EnableVideoPlaybackTranscoding": True,
            "EnablePlaybackRemuxing": True,
            "EnableContentDownloading": True,
            "EnableRemoteAccess": True,
        }

        current = self.get(f"/Users/{user_id}").json()["Policy"]
        current.update(policy_patch)
        self.set_policy(user_id, current)
