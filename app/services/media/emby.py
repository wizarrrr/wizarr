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

    def statistics(self):
        """Return comprehensive Emby server statistics.
        
        Returns:
            dict: Server statistics including library counts, user activity, etc.
        """
        try:
            stats = {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {}
            }
            
            # Library statistics
            try:
                libraries = self.get("/Library/MediaFolders").json()["Items"]
                library_stats = {}
                
                for lib in libraries:
                    lib_type = lib.get("CollectionType", "mixed")
                    if lib_type not in library_stats:
                        library_stats[lib_type] = {
                            "count": 0,
                            "sections": []
                        }
                    
                    # Get item count for this library
                    try:
                        items_response = self.get(f"/Items", params={
                            "ParentId": lib["Id"],
                            "Recursive": "true",
                            "IncludeItemTypes": "Movie,Series,Episode,Audio,Book",
                            "EnableTotalRecordCount": "true",
                            "Limit": 1
                        }).json()
                        
                        item_count = items_response.get("TotalRecordCount", 0)
                        library_stats[lib_type]["count"] += item_count
                        library_stats[lib_type]["sections"].append({
                            "name": lib["Name"],
                            "size": item_count,
                            "id": lib["Id"]
                        })
                    except Exception as e:
                        logging.warning(f"Failed to get size for library {lib['Name']}: {e}")
                        library_stats[lib_type]["sections"].append({
                            "name": lib["Name"],
                            "size": 0,
                            "id": lib["Id"]
                        })
                
                stats["library_stats"] = library_stats
            except Exception as e:
                logging.error(f"Failed to get Emby library stats: {e}")
                stats["library_stats"] = {}
            
            # User statistics
            try:
                users = self.get("/Users").json()
                total_users = len(users)
                
                # Get active sessions
                sessions = self.get("/Sessions").json()
                active_sessions = [s for s in sessions if s.get("NowPlayingItem")]
                active_users = len(set(s.get("UserName", "Unknown") for s in active_sessions))
                
                stats["user_stats"] = {
                    "total_users": total_users,
                    "active_users": active_users,
                    "active_sessions": len(active_sessions)
                }
            except Exception as e:
                logging.error(f"Failed to get Emby user stats: {e}")
                stats["user_stats"] = {
                    "total_users": 0,
                    "active_users": 0,
                    "active_sessions": 0
                }
            
            # Server statistics
            try:
                system_info = self.get("/System/Info").json()
                
                # Count transcoding sessions
                sessions = self.get("/Sessions").json()
                transcoding_sessions = [s for s in sessions if s.get("TranscodingInfo")]
                
                stats["server_stats"] = {
                    "version": system_info.get("Version", "Unknown"),
                    "server_name": system_info.get("ServerName", "Unknown"),
                    "operating_system": system_info.get("OperatingSystem", "Unknown"),
                    "transcoding_sessions": len(transcoding_sessions),
                    "total_sessions": len(sessions)
                }
            except Exception as e:
                logging.error(f"Failed to get Emby server stats: {e}")
                stats["server_stats"] = {}
            
            # Content statistics
            try:
                content_stats = {
                    "recently_added": [],
                    "continue_watching": [],
                    "popular": []
                }
                
                # Get recently added items
                try:
                    recent_response = self.get("/Items/Latest", params={
                        "Limit": 5,
                        "Fields": "DateCreated,PrimaryImageAspectRatio"
                    }).json()
                    
                    for item in recent_response:
                        content_stats["recently_added"].append({
                            "title": item.get("Name", "Unknown"),
                            "type": item.get("Type", "unknown").lower(),
                            "added_at": item.get("DateCreated"),
                            "library": item.get("ParentId", "Unknown")
                        })
                except Exception as e:
                    logging.warning(f"Failed to get recently added: {e}")
                
                # Get items from Continue Watching (resume points)
                try:
                    resume_response = self.get("/Items/Resume", params={
                        "Limit": 5,
                        "MediaTypes": "Video"
                    }).json()
                    
                    for item in resume_response.get("Items", []):
                        content_stats["continue_watching"].append({
                            "title": item.get("Name", "Unknown"),
                            "type": item.get("Type", "unknown").lower(),
                            "progress": item.get("UserData", {}).get("PlayedPercentage", 0),
                            "library": item.get("ParentId", "Unknown")
                        })
                except Exception as e:
                    logging.warning(f"Failed to get continue watching: {e}")
                
                stats["content_stats"] = content_stats
            except Exception as e:
                logging.error(f"Failed to get Emby content stats: {e}")
                stats["content_stats"] = {}
            
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
