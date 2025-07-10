import datetime
import logging
import re
from sqlalchemy import or_

import requests

from app.extensions import db
from app.models import Invitation, User, Settings, Library
from app.services.notifications import notify
from app.services.invites import is_invite_valid, mark_server_used
from .client_base import RestApiMixin, register_media_client

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")


@register_media_client("jellyfin")
class JellyfinClient(RestApiMixin):
    """Wrapper around the Jellyfin REST API using credentials from Settings."""

    def __init__(self, *args, **kwargs):
        # Ensure default url/token keys if caller didn't override.
        if "url_key" not in kwargs:
            kwargs["url_key"] = "server_url"
        if "token_key" not in kwargs:
            kwargs["token_key"] = "api_key"

        super().__init__(*args, **kwargs)

    # RestApiMixin overrides -------------------------------------------

    def _headers(self) -> dict[str, str]:  # type: ignore[override]
        return {"X-Emby-Token": self.token} if self.token else {}

    def libraries(self) -> dict[str, str]:
        return {
            item["Id"]: item["Name"]
            for item in self.get("/Library/MediaFolders").json()["Items"]
        }

    def create_user(self, username: str, password: str) -> str:
        return self.post(
            "/Users/New",
            json={"Name": username, "Password": password}
        ).json()["Id"]

    def set_policy(self, user_id: str, policy: dict) -> None:
        self.post(f"/Users/{user_id}/Policy", json=policy)

    def delete_user(self, user_id: str) -> None:
        self.delete(f"/Users/{user_id}")

    def get_user(self, jf_id: str) -> dict:
        return self.get(f"/Users/{jf_id}").json()

    def update_user(self, jf_id: str, form: dict) -> dict | None:
        current = self.get_user(jf_id)

        for key, val in form.items():
            for section in ("Policy", "Configuration"):
                if key in current[section]:
                    target = current[section][key]
                    if isinstance(target, bool):
                        val = (val == "True")
                    elif isinstance(target, int):
                        val = int(val)
                    elif isinstance(target, list):
                        val = [] if val == "" else val.split(", ")
                    current[section][key] = val

        return self.post(f"/Users/{jf_id}", json=current).json()

    def list_users(self) -> list[User]:
        """Sync users from Jellyfin into the local DB and return the list of User records."""
        jf_users = {u["Id"]: u for u in self.get("/Users").json()}

        for jf in jf_users.values():
            existing = User.query.filter_by(token=jf["Id"]).first()
            if not existing:
                new = User(
                    token=jf["Id"],
                    username=jf["Name"],
                    email="empty",
                    code="empty",
                    password="empty"
                )
                db.session.add(new)
        db.session.commit()

        for dbu in User.query.all():
            if dbu.token not in jf_users:
                db.session.delete(dbu)
        db.session.commit()

    def list_users(self) -> list[User]:
        """Sync users from Jellyfin into the local DB and return the list of User records."""
        jf_users = {u["Id"]: u for u in self.get("/Users").json()}

        for jf in jf_users.values():
            existing = User.query.filter_by(token=jf["Id"], server_id=getattr(self, 'server_id', None)).first()
            if not existing:
                new = User(
                    token=jf["Id"],
                    username=jf["Name"],
                    email="empty",
                    code="empty",
                    server_id=getattr(self, 'server_id', None),
                )
                db.session.add(new)
        db.session.commit()

        # delete local users for this server that no longer exist upstream
        to_check = (
            User.query
            .filter(User.server_id == getattr(self, 'server_id', None))
            .all()
        )
        for dbu in to_check:
            if dbu.token not in jf_users:
                db.session.delete(dbu)
        db.session.commit()

        return User.query.filter(User.server_id == getattr(self, 'server_id', None)).all()

    # --- helpers -----------------------------------------------------

    def _password_for_db(self, password: str) -> str:
        """Return the password value to store in the local DB."""
        return password

    @staticmethod
    def _mark_invite_used(inv: Invitation, user: User) -> None:
        """Mark invitation consumed for the Jellyfin server only."""
        inv.used_by = user
        mark_server_used(inv, getattr(user, "server_id", None) or (inv.server.id if inv.server else None))

    @staticmethod
    def _folder_name_to_id(name: str, cache: dict[str, str]) -> str | None:
        """Resolve a folder name or ID to the server ID."""

        # Allow passing the actual ID directly
        if name in cache.values():
            return name

        return cache.get(name)

    def _set_specific_folders(self, user_id: str, names: list[str]):
        mapping = {
            item["Name"]: item["Id"]
            for item in self.get("/Library/MediaFolders").json()["Items"]
        }

        # Also map IDs directly for convenience
        mapping.update({v: v for v in mapping.values()})

        folder_ids = [self._folder_name_to_id(n, mapping) for n in names]
        folder_ids = [fid for fid in folder_ids if fid]

        policy_patch = {
            "EnableAllFolders": not folder_ids,
            "EnabledFolders": folder_ids,
        }

        current = self.get(f"/Users/{user_id}").json()["Policy"]
        current.update(policy_patch)
        self.set_policy(user_id, current)

    # --- public sign-up ---------------------------------------------

    def join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
        if not EMAIL_RE.fullmatch(email):
            return False, "Invalid e-mail address."
        if not 8 <= len(password) <= 20:
            return False, "Password must be 8–20 characters."
        if password != confirm:
            return False, "Passwords do not match."

        ok, msg = is_invite_valid(code)
        if not ok:
            return False, msg

        existing = User.query.filter(
            or_(User.username == username, User.email == email),
            User.server_id == getattr(self, 'server_id', None)
        ).first()
        if existing:
            return False, "User or e-mail already exists."

        try:
            user_id = self.create_user(username, password)

            inv = Invitation.query.filter_by(code=code).first()

            if inv.libraries:
                sections = [lib.external_id for lib in inv.libraries if lib.server_id == (inv.server.id if inv.server else None)]
            else:
                sections = [
                    lib.external_id
                    for lib in Library.query.filter_by(enabled=True, server_id=inv.server.id if inv.server else None).all()
                ]

            self._set_specific_folders(user_id, sections)

            # Apply download / Live TV permissions
            allow_downloads = bool(getattr(inv, 'jellyfin_allow_downloads', False))
            allow_live_tv   = bool(getattr(inv, 'jellyfin_allow_live_tv', False))
            # fall back to server defaults if invite flags are false
            if inv.server:
                if not allow_downloads:
                    allow_downloads = bool(getattr(inv.server, 'allow_downloads_jellyfin', False))
                if not allow_live_tv:
                    allow_live_tv   = bool(getattr(inv.server, 'allow_tv_jellyfin', False))
            
            if allow_downloads or allow_live_tv:
                current_policy = self.get(f"/Users/{user_id}").json().get("Policy", {})
                if allow_downloads:
                    current_policy["EnableDownloads"] = True
                if allow_live_tv:
                    current_policy["EnableLiveTvAccess"] = True
                self.set_policy(user_id, current_policy)

            expires = None
            if inv.duration:
                days = int(inv.duration)
                expires = datetime.datetime.utcnow() + datetime.timedelta(days=days)

            new_user = User(
                username=username,
                email=email,
                token=user_id,
                code=code,
                expires=expires,
                server_id=inv.server.id if inv.server else None,
            )
            db.session.add(new_user)
            db.session.commit()

            self._mark_invite_used(inv, new_user)
            notify(
                "New User",
                f"User {username} has joined your server! 🎉",
                tags="tada",
            )

            return True, ""

        except Exception:  # noqa: BLE001
            logging.error("Jellyfin join error", exc_info=True)
            db.session.rollback()
            return False, "An unexpected error occurred."

    def now_playing(self) -> list[dict]:
        """Return a list of currently playing sessions from Jellyfin.
        
        Returns:
            list: A list of session dictionaries with standardized keys.
        """
        try:
            sessions = self.get("/Sessions").json()
            now_playing_sessions = []
            
            for session in sessions:
                # Only include sessions that are actually playing media
                if session.get("NowPlayingItem") is None:
                    continue
                    
                now_playing_item = session["NowPlayingItem"]
                play_state = session.get("PlayState", {})
                
                # Calculate progress (0.0 to 1.0)
                progress = 0.0
                if play_state.get("PositionTicks") and now_playing_item.get("RunTimeTicks"):
                    progress = play_state["PositionTicks"] / now_playing_item["RunTimeTicks"]
                    progress = max(0.0, min(1.0, progress))  # Clamp between 0 and 1
                
                # Determine media type
                media_type = now_playing_item.get("Type", "unknown").lower()
                
                # Get media title - handle different types
                media_title = now_playing_item.get("Name", "Unknown")
                if media_type == "episode":
                    # For TV episodes, include series and episode info
                    series_name = now_playing_item.get("SeriesName", "")
                    season_num = now_playing_item.get("ParentIndexNumber", "")
                    episode_num = now_playing_item.get("IndexNumber", "")
                    if series_name:
                        media_title = f"{series_name}"
                        if season_num and episode_num:
                            media_title += f" S{season_num:02d}E{episode_num:02d}"
                        media_title += f" - {now_playing_item.get('Name', '')}"
                
                # Get playback state
                state = "stopped"
                if play_state.get("IsPaused"):
                    state = "paused"
                elif play_state.get("PositionTicks") is not None:
                    state = "playing"
                
                # Get user info
                user_info = session.get("UserName", "Unknown User")
                
                # Get session ID
                session_id = session.get("Id", "")
                
                # Get artwork URL
                artwork_url = None
                item_id = now_playing_item.get("Id")
                if item_id:
                    # Use Primary image type for poster/thumbnail
                    artwork_url = f"{self.url}/Items/{item_id}/Images/Primary"
                    if self.token:
                        artwork_url += f"?api_key={self.token}"
                
                # Get transcoding information
                transcoding_info = {
                    "is_transcoding": False,
                    "video_codec": None,
                    "audio_codec": None,
                    "container": None,
                    "video_resolution": None,
                    "transcoding_speed": None,
                    "direct_play": True
                }
                
                # Check transcoding info from session
                if session.get("TranscodingInfo"):
                    transcode_info = session["TranscodingInfo"]
                    transcoding_info["is_transcoding"] = True
                    transcoding_info["direct_play"] = False
                    transcoding_info["video_codec"] = transcode_info.get("VideoCodec")
                    transcoding_info["audio_codec"] = transcode_info.get("AudioCodec")
                    transcoding_info["container"] = transcode_info.get("Container")
                    transcoding_info["transcoding_speed"] = transcode_info.get("TranscodingFramerate")
                
                # Check for direct stream vs transcode
                if session.get("PlayMethod"):
                    play_method = session["PlayMethod"]
                    if play_method == "DirectPlay":
                        transcoding_info["direct_play"] = True
                        transcoding_info["is_transcoding"] = False
                    elif play_method in ["DirectStream", "Transcode"]:
                        transcoding_info["direct_play"] = False
                        if play_method == "Transcode":
                            transcoding_info["is_transcoding"] = True
                
                # Get media stream info
                if now_playing_item.get("MediaStreams"):
                    for stream in now_playing_item["MediaStreams"]:
                        if stream.get("Type") == "Video" and not transcoding_info["video_codec"]:
                            transcoding_info["video_codec"] = stream.get("Codec")
                            transcoding_info["video_resolution"] = stream.get("DisplayTitle") or f"{stream.get('Width', '?')}x{stream.get('Height', '?')}"
                        elif stream.get("Type") == "Audio" and not transcoding_info["audio_codec"]:
                            transcoding_info["audio_codec"] = stream.get("Codec")
                
                # Get container info
                if not transcoding_info["container"]:
                    transcoding_info["container"] = now_playing_item.get("Container")
                
                # Build standardized session info
                session_info = {
                    "user_name": user_info,
                    "media_title": media_title,
                    "media_type": media_type,
                    "progress": progress,
                    "state": state,
                    "session_id": session_id,
                    "client": session.get("Client", ""),
                    "device_name": session.get("DeviceName", ""),
                    "position_ms": play_state.get("PositionTicks", 0) // 10000,  # Convert from ticks to ms
                    "duration_ms": now_playing_item.get("RunTimeTicks", 0) // 10000,  # Convert from ticks to ms
                    "artwork_url": artwork_url,
                    "transcoding": transcoding_info,
                }
                
                now_playing_sessions.append(session_info)
                
            return now_playing_sessions
            
        except Exception as e:
            logging.error(f"Failed to get now playing from Jellyfin: {e}")
            return []

    def statistics(self):
        """Return comprehensive Jellyfin server statistics.
        
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
                logging.error(f"Failed to get Jellyfin library stats: {e}")
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
                logging.error(f"Failed to get Jellyfin user stats: {e}")
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
                    "total_sessions": len(sessions),
                    "startup_wizard_completed": system_info.get("StartupWizardCompleted", False)
                }
            except Exception as e:
                logging.error(f"Failed to get Jellyfin server stats: {e}")
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
                logging.error(f"Failed to get Jellyfin content stats: {e}")
                stats["content_stats"] = {}
            
            return stats
            
        except Exception as e:
            logging.error(f"Failed to get Jellyfin statistics: {e}")
            return {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
                "error": str(e)
            }

# ─── Admin-side helpers – mirror the Plex API we already exposed ──────────
