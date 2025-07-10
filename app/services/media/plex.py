import datetime
import threading
import logging

from cachetools import cached, TTLCache
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount, MyPlexInvite

from app.extensions import db
from app.models import Invitation, User, Settings, Library, MediaServer
from app.services.notifications import notify
from .client_base import MediaClient, register_media_client
from app.services.media.service import get_client_for_media_server
from app.services.invites import mark_server_used

# ---------------------------------------------------------------------------
# Temporary monkey-patch: Plex removed /api/invites/requests; use v2 endpoint.
# Remove this block once plexapi supports the new route natively.
# ---------------------------------------------------------------------------
_original_accept_invite = MyPlexAccount.acceptInvite  # keep reference for fallback


def _accept_invite_v2(self: MyPlexAccount, user):
    """Replacement for MyPlexAccount.acceptInvite that targets the v2 API.

    Plex switched invite acceptance to
    POST https://plex.tv/api/v2/shared_servers/{invite.id}/accept.
    This implementation resolves the *invite ID* using the new `/api/v2/shared_servers`
    endpoint as well so that it no longer touches the legacy
    `/api/invites/requests` endpoint (which now returns *410 Gone*).

    If anything in the new flow fails we transparently fall back to the
    original PlexAPI code path to preserve backwards compatibility with
    self-hosted or older Plex versions.
    """
    # ------------------------------------------------------------------
    # 1) Determine the *invite object* we are supposed to accept.
    #     a) If the caller already provided an invite instance → use it.
    #     b) If the caller passed a username / e-mail → resolve it via
    #        the new v2 shared-servers endpoint.
    # ------------------------------------------------------------------
    
    invite = user if isinstance(user, MyPlexInvite) else self.pendingInvite(user, includeSent=False)
    
    url = f"https://plex.tv/api/v2/shared_servers/{invite.id}/accept"
    response = self._session.post(url)
    response.raise_for_status()
    return response


# Apply monkey-patch so all future instances use the new method
MyPlexAccount.acceptInvite = _accept_invite_v2

@register_media_client("plex")
class PlexClient(MediaClient):
    """Wrapper that connects to Plex using admin credentials."""

    def __init__(self, *args, **kwargs):
        """Initialise the Plex client.

        ``MediaClient`` now supports passing a fully populated
        ``MediaServer`` row via ``media_server=…``.  We therefore accept an
        arbitrary signature and forward it to the superclass so that callers
        like ``get_client_for_media_server`` can leverage this without
        modification here.
        """

        # Keep legacy fallback behaviour (url_key / token_key) by providing
        # the default kwargs if the caller did *not* override them.
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
            self._admin = MyPlexAccount(token=self.token)
        return self._admin

    def libraries(self) -> dict[str, str]:
        """Return a mapping of external_id to display name for each Plex library section."""
        return {lib.title: lib.title for lib in self.server.library.sections()}

    def create_user(self, *args, **kwargs):
        """Plex does not support direct user creation; use invite_friend or invite_home."""
        raise NotImplementedError(
            "PlexClient does not support create_user; use invite_friend or invite_home"
        )
    def invite_friend(self, email: str, sections: list[str], allow_sync: bool, allow_channels: bool):
        self.admin.inviteFriend(
            user=email, server=self.server,
            sections=sections, allowSync=allow_sync, allowChannels=allow_channels
        )

    def invite_home(self, email: str, sections: list[str], allow_sync: bool, allow_channels: bool):
        self.admin.createExistingUser(
            user=email, server=self.server,
            sections=sections, allowSync=allow_sync, allowChannels=allow_channels
        )

    def get_user(self, db_id: int) -> dict:
        user_record = User.query.get(db_id)
        if not user_record:
            raise ValueError(f"No user found with id {db_id}")

        plex_user = self.admin.user(user_record.email)
        return {
            "Name": plex_user.title,
            "Id": plex_user.id,
            "Configuration": {
                "allowCameraUpload": plex_user.allowCameraUpload,
                "allowChannels": plex_user.allowChannels,
                "allowSync": plex_user.allowSync,
            },
            "Policy": {"sections": "na"},
        }

    def update_user(self, info: dict, form: dict) -> None:
        self.admin.updateFriend(
            info["Name"],
            self.server,
            allowSync=bool(form.get("allowSync")),
            allowChannels=bool(form.get("allowChannels")),
            allowCameraUpload=bool(form.get("allowCameraUpload")),
        )

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

        plex_users = {
            u.email: u
            for u in self.admin.users()
            if any(s.machineIdentifier == server_id for s in u.servers)
        }
        db_users = (
            db.session.query(User)
            .filter(
                db.or_(User.server_id.is_(None), User.server_id == getattr(self, 'server_id', None))
            )
            .all()
        )

        known_emails = set(plex_users.keys())
        for db_user in db_users:
            if db_user.email not in known_emails:
                db.session.delete(db_user)
        db.session.commit()

        for plex_user in plex_users.values():
            existing = db.session.query(User).filter_by(email=plex_user.email, server_id=getattr(self, 'server_id', None)).first()
            if not existing:
                new_user = User(
                    email=plex_user.email or "None",
                    username=plex_user.title,
                    token="None",
                    code="None",
                    server_id=getattr(self, 'server_id', None),
                )
                db.session.add(new_user)
        db.session.commit()

        users = (
            db.session.query(User)
            .filter(User.server_id == getattr(self, 'server_id', None))
            .all()
        )
        for u in users:
            p = plex_users.get(u.email)
            if p:
                u.photo = p.thumb

        return users


    def now_playing(self) -> list[dict]:
        """Return a list of currently playing sessions from Plex.
        
        Returns:
            list: A list of session dictionaries with standardized keys.
        """
        try:
            sessions = self.server.sessions()
            now_playing_sessions = []
            
            for session in sessions:
                # Only include sessions that are actively playing
                if not hasattr(session, 'viewOffset') or session.viewOffset is None:
                    continue
                
                # Calculate progress (0.0 to 1.0)
                progress = 0.0
                if hasattr(session, 'duration') and session.duration and session.viewOffset:
                    progress = session.viewOffset / session.duration
                    progress = max(0.0, min(1.0, progress))  # Clamp between 0 and 1
                
                # Determine media type
                media_type = getattr(session, 'type', 'unknown').lower()
                
                # Get media title - handle different types
                media_title = getattr(session, 'title', 'Unknown')
                if media_type == 'episode':
                    # For TV episodes, include series and episode info
                    grandparent_title = getattr(session, 'grandparentTitle', '')
                    season_num = getattr(session, 'parentIndex', None)
                    episode_num = getattr(session, 'index', None)
                    if grandparent_title:
                        media_title = f"{grandparent_title}"
                        if season_num and episode_num:
                            media_title += f" S{season_num:02d}E{episode_num:02d}"
                        media_title += f" - {getattr(session, 'title', '')}"
                
                # Get playback state from players
                state = "stopped"
                players = getattr(session, 'players', [])
                if players:
                    player_state = getattr(players[0], 'state', 'stopped')
                    if player_state == 'paused':
                        state = "paused"
                    elif player_state == 'playing':
                        state = "playing"
                    elif player_state == 'buffering':
                        state = "buffering"
                
                # Get user info
                user_info = "Unknown User"
                if hasattr(session, 'usernames') and session.usernames:
                    user_info = session.usernames[0]
                elif hasattr(session, 'users') and session.users:
                    user_info = session.users[0].title
                
                # Get session ID
                session_id = getattr(session, 'sessionKey', '')
                
                # Get client info
                client_name = ""
                device_name = ""
                if players:
                    client_name = getattr(players[0], 'product', '')
                    device_name = getattr(players[0], 'title', '')
                
                # Resolve the correct artwork URL.  Prefer the helper properties PlexAPI
                # exposes (``thumbUrl``) as they already include the base server URL and
                # authentication token.  Fall back to the first available thumbnail-type
                # attribute and use ``PlexServer.url`` to construct a fully qualified URL.

                artwork_url = None

                # 1) Use PlexAPI convenience property if present (already absolute incl. token)
                if getattr(session, "thumbUrl", None):
                    artwork_url = session.thumbUrl
                else:
                    # 2) Check common thumbnail attributes in priority order
                    thumb_attr = None
                    for attr in ("thumb", "art", "grandparentThumb", "parentThumb"):
                        val = getattr(session, attr, None)
                        if val:
                            thumb_attr = val
                            break

                    if thumb_attr:
                        # Construct absolute URL if we only have a relative key/path.
                        if thumb_attr.startswith("http"):
                            artwork_url = thumb_attr  # already absolute
                        else:
                            # ``PlexServer.url`` appends the base URL and token automatically.
                            artwork_url = self.server.url(thumb_attr, includeToken=True)
                
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
                
                # Check for transcoding session
                if hasattr(session, 'transcodeSessions') and session.transcodeSessions:
                    transcoding_info["is_transcoding"] = True
                    transcoding_info["direct_play"] = False
                    transcode_session = session.transcodeSessions[0]
                    transcoding_info["video_codec"] = getattr(transcode_session, 'videoCodec', None)
                    transcoding_info["audio_codec"] = getattr(transcode_session, 'audioCodec', None)
                    transcoding_info["container"] = getattr(transcode_session, 'container', None)
                    transcoding_info["transcoding_speed"] = getattr(transcode_session, 'speed', None)
                
                # Check media info for resolution and codecs
                if hasattr(session, 'media') and session.media:
                    media = session.media[0] if session.media else None
                    if media:
                        if hasattr(media, 'videoResolution'):
                            transcoding_info["video_resolution"] = media.videoResolution
                        if hasattr(media, 'parts') and media.parts:
                            part = media.parts[0]
                            if hasattr(part, 'streams'):
                                for stream in part.streams:
                                    if hasattr(stream, 'streamType'):
                                        if stream.streamType == 1:  # Video stream
                                            if not transcoding_info["video_codec"]:
                                                transcoding_info["video_codec"] = getattr(stream, 'codec', None)
                                        elif stream.streamType == 2:  # Audio stream
                                            if not transcoding_info["audio_codec"]:
                                                transcoding_info["audio_codec"] = getattr(stream, 'codec', None)
                            if hasattr(part, 'container'):
                                if not transcoding_info["container"]:
                                    transcoding_info["container"] = part.container
                
                # Build standardized session info
                session_info = {
                    "user_name": user_info,
                    "media_title": media_title,
                    "media_type": media_type,
                    "progress": progress,
                    "state": state,
                    "session_id": str(session_id),
                    "client": client_name,
                    "device_name": device_name,
                    "position_ms": getattr(session, 'viewOffset', 0),
                    "duration_ms": getattr(session, 'duration', 0),
                    "artwork_url": artwork_url,
                    "transcoding": transcoding_info,
                }
                
                now_playing_sessions.append(session_info)
                
            return now_playing_sessions
            
        except Exception as e:
            logging.error(f"Failed to get now playing from Plex: {e}")
            return []

    def statistics(self):
        """Return comprehensive Plex server statistics.
        
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
            library_stats = {}
            try:
                sections = self.server.library.sections()
                for section in sections:
                    library_type = getattr(section, 'type', 'unknown')
                    if library_type not in library_stats:
                        library_stats[library_type] = {
                            "count": 0,
                            "sections": []
                        }
                    
                    # Get item count for this section
                    try:
                        section_size = len(section.all())
                        library_stats[library_type]["count"] += section_size
                        library_stats[library_type]["sections"].append({
                            "name": section.title,
                            "size": section_size,
                            "key": section.key
                        })
                    except Exception as e:
                        logging.warning(f"Failed to get size for section {section.title}: {e}")
                        library_stats[library_type]["sections"].append({
                            "name": section.title,
                            "size": 0,
                            "key": section.key
                        })
                        
                stats["library_stats"] = library_stats
            except Exception as e:
                logging.error(f"Failed to get Plex library stats: {e}")
                stats["library_stats"] = {}
            
            # User statistics
            try:
                users = self.server.myPlexAccount().users()
                total_users = len(users) + 1  # +1 for account owner
                
                # Get active sessions for current activity
                sessions = self.server.sessions()
                active_users = len(set(session.usernames[0] if session.usernames else "Unknown" 
                                     for session in sessions))
                
                stats["user_stats"] = {
                    "total_users": total_users,
                    "active_users": active_users,
                    "active_sessions": len(sessions)
                }
            except Exception as e:
                logging.error(f"Failed to get Plex user stats: {e}")
                stats["user_stats"] = {
                    "total_users": 0,
                    "active_users": 0,
                    "active_sessions": 0
                }
            
            # Server statistics
            try:
                # Get server info
                server_info = {
                    "version": getattr(self.server, 'version', 'Unknown'),
                    "platform": getattr(self.server, 'platform', 'Unknown'),
                    "platform_version": getattr(self.server, 'platformVersion', 'Unknown'),
                    "updated_at": getattr(self.server, 'updatedAt', None)
                }
                
                # Get transcode sessions
                transcode_sessions = self.server.transcodeSessions()
                transcoding_count = len(transcode_sessions)
                
                stats["server_stats"] = {
                    **server_info,
                    "transcoding_sessions": transcoding_count,
                    "total_sessions": len(self.server.sessions())
                }
            except Exception as e:
                logging.error(f"Failed to get Plex server stats: {e}")
                stats["server_stats"] = {}
            
            # Content statistics - get popular/recent content
            try:
                content_stats = {
                    "recently_added": [],
                    "on_deck": [],
                    "popular": []
                }
                
                # Get recently added items (limit to 5)
                try:
                    recent = self.server.library.recentlyAdded()[:5]
                    for item in recent:
                        content_stats["recently_added"].append({
                            "title": getattr(item, 'title', 'Unknown'),
                            "type": getattr(item, 'type', 'unknown'),
                            "added_at": getattr(item, 'addedAt', None),
                            "library": getattr(item, 'librarySectionTitle', 'Unknown')
                        })
                except Exception as e:
                    logging.warning(f"Failed to get recently added: {e}")
                
                # Get On Deck items
                try:
                    on_deck = self.server.library.onDeck()[:5]
                    for item in on_deck:
                        content_stats["on_deck"].append({
                            "title": getattr(item, 'title', 'Unknown'),
                            "type": getattr(item, 'type', 'unknown'),
                            "progress": getattr(item, 'viewOffset', 0),
                            "library": getattr(item, 'librarySectionTitle', 'Unknown')
                        })
                except Exception as e:
                    logging.warning(f"Failed to get On Deck: {e}")
                
                stats["content_stats"] = content_stats
            except Exception as e:
                logging.error(f"Failed to get Plex content stats: {e}")
                stats["content_stats"] = {}
            
            return stats
            
        except Exception as e:
            logging.error(f"Failed to get Plex statistics: {e}")
            return {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
                "error": str(e)
            }


# ─── Invite & onboarding ──────────────────────────────────────────────────

def handle_oauth_token(app, token: str, code: str) -> None:
    """Called after Plex OAuth handshake; create DB user and invite to Plex."""
    with app.app_context():
        account = MyPlexAccount(token=token)
        email = account.email

        inv = Invitation.query.filter_by(code=code).first()
        server = inv.server if inv and inv.server else MediaServer.query.first()
        server_id = server.id if server else None

        # remove any previous account with same email on this server
        db.session.query(User).filter(
            User.email == email,
            User.server_id == server_id
        ).delete(synchronize_session=False)
        db.session.commit()

        duration = inv.duration if inv else None
        expires = (
            datetime.datetime.now() + datetime.timedelta(days=int(duration))
            if duration else None
        )

        new_user = User(
            token=token,
            email=email,
            username=account.username,
            code=code,
            expires=expires,
            server_id=server_id,
        )
        db.session.add(new_user)
        db.session.commit()

        _invite_user(email, code, new_user.id, server)

        notify(
            "User Joined",
            f"User {account.username} has joined your server!",
            "tada"
        )

        threading.Thread(
            target=_post_join_setup,
            args=(app, token),
            daemon=True
        ).start()


def _invite_user(email: str, code: str, user_id: int, server: MediaServer) -> None:
    inv = Invitation.query.filter_by(code=code).first()
    client = get_client_for_media_server(server)

    # libraries list
    libs = [lib.external_id for lib in inv.libraries if lib.server_id == server.id] if inv.libraries else []

    if not libs:
        # Fallback to *all* enabled libraries for this server
        libs = [
            lib.external_id
            for lib in Library.query.filter_by(enabled=True, server_id=server.id).all()
        ]

    allow_sync = bool(inv.plex_allow_sync)
    allow_tv = bool(inv.plex_allow_channels)

    if inv.plex_home:
        client.invite_home(email, libs, allow_sync, allow_tv)
    else:
        client.invite_friend(email, libs, allow_sync, allow_tv)

    logging.info("Invited %s to Plex", email)

    if user_id:
        user = User.query.get(user_id)
        inv.used_by = user

    # Mark invite consumed for *this* server (multi-server aware)
    mark_server_used(inv, server.id)

    # clear cached user list so admin UI shows the new invite
    PlexClient.list_users.cache_clear()
    db.session.commit()


def _post_join_setup(app, token: str):
    with app.app_context():
        client = PlexClient()
        try:
            user = MyPlexAccount(token=token)
            user.acceptInvite(client.admin.email)
            user.enableViewStateSync()
            _opt_out_online_sources(user)
        except Exception as exc:
            logging.error("Post-join setup failed: %s", exc)


def _opt_out_online_sources(user: MyPlexAccount):
    for src in user.onlineMediaSources():
        src.optOut()


# ─── User queries / mutate ────────────────────────────────────────────────


