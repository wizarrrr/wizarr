import datetime
import logging
import re

import requests
from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, Library, User
from app.services.invites import is_invite_valid, mark_server_used
from app.services.notifications import notify

from .client_base import RestApiMixin, register_media_client

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")


@register_media_client("jellyfin")
class JellyfinClient(RestApiMixin):
    """Wrapper around the Jellyfin REST API using credentials from Settings."""

    def __init__(self, *args, **kwargs):
        if "url_key" not in kwargs:
            kwargs["url_key"] = "server_url"
        if "token_key" not in kwargs:
            kwargs["token_key"] = "api_key"

        super().__init__(*args, **kwargs)

    def _headers(self) -> dict[str, str]:  # type: ignore[override]
        return {"X-Emby-Token": self.token} if self.token else {}

    def libraries(self) -> dict[str, str]:
        return {
            item["Id"]: item["Name"]
            for item in self.get("/Library/MediaFolders").json()["Items"]
        }

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        if url and token:
            headers = {"X-Emby-Token": token}
            response = requests.get(
                f"{url.rstrip('/')}/Library/MediaFolders", headers=headers, timeout=10
            )
            response.raise_for_status()
            items = response.json()["Items"]
        else:
            items = self.get("/Library/MediaFolders").json()["Items"]

        return {item["Name"]: item["Id"] for item in items}

    def create_user(self, username: str, password: str) -> str:
        return self.post(
            "/Users/New", json={"Name": username, "Password": password}
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

    def list_users(self) -> list[User]:
        server_id = getattr(self, "server_id", None)
        jf_users = {u["Id"]: u for u in self.get("/Users").json()}

        for jf in jf_users.values():
            existing = User.query.filter_by(token=jf["Id"]).first()
            if not existing:
                new = User(
                    token=jf["Id"],
                    username=jf["Name"],
                    email="empty",
                    code="empty",
                    server_id=server_id,
                )
                db.session.add(new)

        to_check = User.query.filter(User.server_id == server_id).all()
        for dbu in to_check:
            if dbu.token not in jf_users:
                db.session.delete(dbu)

        db.session.commit()
        return User.query.filter(User.server_id == server_id).all()

    def _password_for_db(self, password: str) -> str:
        return password

    @staticmethod
    def _mark_invite_used(inv: Invitation, user: User) -> None:
        inv.used_by = user  # type: ignore[assignment]
        mark_server_used(inv, user.server_id)

    @staticmethod
    def _folder_name_to_id(name: str, cache: dict[str, str]) -> str | None:
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
            else:
                sections = [
                    lib.external_id
                    for lib in Library.query.filter_by(
                        enabled=True, server_id=server_id
                    ).all()
                ]

            self._set_specific_folders(user_id, sections)

            # Use universal columns
            allow_downloads = bool(getattr(inv, "allow_downloads", False))
            allow_live_tv = bool(getattr(inv, "allow_live_tv", False))

            if server_id:
                from app.models import MediaServer

                current_server = MediaServer.query.get(server_id)
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
            current_policy["EnableDownloads"] = allow_downloads
            current_policy["EnableLiveTvAccess"] = allow_live_tv
            self.set_policy(user_id, current_policy)

            expires = None
            if inv and inv.duration:
                expires = datetime.datetime.utcnow() + datetime.timedelta(
                    days=int(inv.duration)
                )

            new_user = self._create_user_with_identity_linking(
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

            if inv:
                self._mark_invite_used(inv, new_user)
            notify(
                "New User", f"User {username} has joined your server! 🎉", tags="tada"
            )

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

        try:
            poster_response = self.get(
                f"/Items/{poster_item_id}/RemoteImages",
                params={"type": "Primary", "limit": 2},
            ).json()

            artwork_url = fallback_artwork_url = thumbnail_url = None

            if poster_response.get("Images"):
                images = poster_response["Images"]
                if images:
                    artwork_url = images[0].get("Url")
                    fallback_artwork_url = images[0].get("ThumbnailUrl") or artwork_url

            try:
                backdrop_response = self.get(
                    f"/Items/{poster_item_id}/RemoteImages",
                    params={"type": "Backdrop", "limit": 1},
                ).json()

                if backdrop_response.get("Images"):
                    thumbnail_url = backdrop_response["Images"][0].get("Url")
            except Exception:
                pass

            if not thumbnail_url:
                thumbnail_url = fallback_artwork_url

            return {
                "artwork_url": artwork_url,
                "fallback_artwork_url": fallback_artwork_url,
                "thumbnail_url": thumbnail_url,
            }

        except Exception as e:
            logging.warning(f"Failed to get remote images for item {item_id}: {e}")

            base_params = f"?api_key={self.token}" if self.token else ""
            fallback_url = (
                f"{self.url}/Items/{poster_item_id}/Images/Primary{base_params}"
            )
            return {
                "artwork_url": fallback_url,
                "fallback_artwork_url": fallback_url,
                "thumbnail_url": fallback_url,
            }

    def now_playing(self) -> list[dict]:
        try:
            sessions = self.get("/Sessions").json()
            now_playing_sessions = []

            for session in sessions:
                if session.get("NowPlayingItem") is None:
                    continue

                now_playing_item = session["NowPlayingItem"]
                play_state = session.get("PlayState", {})

                progress = 0.0
                if play_state.get("PositionTicks") and now_playing_item.get(
                    "RunTimeTicks"
                ):
                    progress = max(
                        0.0,
                        min(
                            1.0,
                            play_state["PositionTicks"]
                            / now_playing_item["RunTimeTicks"],
                        ),
                    )

                media_type = now_playing_item.get("Type", "unknown").lower()

                media_title = now_playing_item.get("Name", "Unknown")
                if media_type == "episode":
                    series_name = now_playing_item.get("SeriesName", "")
                    season_num = now_playing_item.get("ParentIndexNumber", "")
                    episode_num = now_playing_item.get("IndexNumber", "")
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

                user_info = session.get("UserName", "Unknown User")
                session_id = session.get("Id", "")

                item_id = now_playing_item.get("Id")
                series_id = now_playing_item.get("SeriesId")
                artwork_info = self._get_artwork_urls(item_id, media_type, series_id)

                transcoding_info = {
                    "is_transcoding": False,
                    "video_codec": None,
                    "audio_codec": None,
                    "container": None,
                    "video_resolution": None,
                    "transcoding_speed": None,
                    "direct_play": True,
                }

                if session.get("TranscodingInfo"):
                    transcode_info = session["TranscodingInfo"]
                    transcoding_info["is_transcoding"] = True
                    transcoding_info["direct_play"] = False
                    transcoding_info["video_codec"] = transcode_info.get("VideoCodec")
                    transcoding_info["audio_codec"] = transcode_info.get("AudioCodec")
                    transcoding_info["container"] = transcode_info.get("Container")
                    transcoding_info["transcoding_speed"] = transcode_info.get(
                        "TranscodingFramerate"
                    )

                if session.get("PlayMethod"):
                    play_method = session["PlayMethod"]
                    if play_method == "DirectPlay":
                        transcoding_info["direct_play"] = True
                        transcoding_info["is_transcoding"] = False
                    elif play_method in ["DirectStream", "Transcode"]:
                        transcoding_info["direct_play"] = False
                        if play_method == "Transcode":
                            transcoding_info["is_transcoding"] = True

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

                session_info = {
                    "user_name": user_info,
                    "media_title": media_title,
                    "media_type": media_type,
                    "progress": progress,
                    "state": state,
                    "session_id": session_id,
                    "client": session.get("Client", ""),
                    "device_name": session.get("DeviceName", ""),
                    "position_ms": play_state.get("PositionTicks", 0) // 10000,
                    "duration_ms": now_playing_item.get("RunTimeTicks", 0) // 10000,
                    "artwork_url": artwork_info["artwork_url"],
                    "fallback_artwork_url": artwork_info["fallback_artwork_url"],
                    "thumbnail_url": artwork_info["thumbnail_url"],
                    "transcoding": transcoding_info,
                }

                now_playing_sessions.append(session_info)

            return now_playing_sessions

        except Exception as e:
            logging.error(f"Failed to get now playing from Jellyfin: {e}")
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


# ─── Admin-side helpers – mirror the Plex API we already exposed ──────────
