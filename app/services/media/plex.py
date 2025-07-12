import datetime
import threading
import logging

from cachetools import cached, TTLCache
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount

from app.extensions import db
from app.models import Invitation, User, Settings, Library, MediaServer
from app.services.notifications import notify
from .client_base import MediaClient, register_media_client
from app.services.media.service import get_client_for_media_server
from app.services.invites import mark_server_used

# ---------------------------------------------------------------------------
# Monkey-patch: acceptInvite that uses /api/v2/shared_servers routes
# ---------------------------------------------------------------------------
def _accept_invite_v2(self: MyPlexAccount, owner):
    """
    Accept a pending server share via the v2 API
    (list → accept) without hitting the deprecated v1 endpoint.
    """

    base = "https://clients.plex.tv"

    # 1) Build the full identity query-string Plex expects.
    #    Plex returns HTTP 400 unless *all* usual X-Plex-* fields are present
    #    in the **query string**.  The session headers created by PlexAPI
    #    contain only a subset (sometimes just the token), so we copy what is
    #    there *and* add sensible defaults for the rest.

    params = {
        k: v
        for k, v in self._session.headers.items()
        if k.startswith("X-Plex-") and k != "X-Plex-Provides"
    }

    # ------------------------------------------------------------------
    # Fill in any missing identity fields with fall-back values.  They do
    # not need to be perfect – Plex validates presence, not content.
    # ------------------------------------------------------------------
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

    # ensure we always pass a valid token
    params["X-Plex-Token"] = self.authToken

    # 2) Normal headers – we keep Accept here, *not* on the query-string
    hdrs = {"Accept": "application/json"}

    # ---- list pending invites ------------------------------------------------
    url_list = f"{base}/api/v2/shared_servers/invites/received/pending"
    resp = self._session.get(url_list, params=params, headers=hdrs)
    resp.raise_for_status()
    invites = resp.json()                             # list[dict]

    # ---- find the invite that matches the owner we were given ---------------
    def _matches(inv):
        o = inv.get("owner", {})
        return owner in (o.get("username"), o.get("email"), o.get("title"), o.get("friendlyName"))

    try:
        inv = next(i for i in invites if _matches(i))
    except StopIteration:
        raise ValueError(f"No pending invite from '{owner}' found")

    # Each invitation can include one or more shared servers; pick the first
    shared_servers = inv.get("sharedServers")
    if not shared_servers:
        raise ValueError("Invite structure missing 'sharedServers' list")

    invite_id = shared_servers[0]["id"]

    # ---- accept it -----------------------------------------------------------
    url_accept = f"{base}/api/v2/shared_servers/{invite_id}/accept"
    resp = self._session.post(url_accept, params=params, headers=hdrs)
    resp.raise_for_status()
    return resp


# Activate the patch
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

    def scan_libraries(self, url: str = None, token: str = None) -> dict[str, str]:
        """Scan available libraries on this Plex server.
        
        Args:
            url: Optional server URL override
            token: Optional API token override
            
        Returns:
            dict: Library name -> library title mapping
        """
        if url and token:
            # Use override credentials for scanning
            try:
                from plexapi.server import PlexServer
                temp_server = PlexServer(url, token)
                return {lib.title: lib.title for lib in temp_server.library.sections()}
            except Exception as e:
                logging.error(f"Failed to scan Plex libraries with override credentials: {e}")
                return {}
        else:
            # Use saved credentials
            return self.libraries()

    def create_user(self, *args, **kwargs):
        """Plex does not support direct user creation; use invite_friend or invite_home."""
        raise NotImplementedError(
            "PlexClient does not support create_user; use invite_friend or invite_home"
        )

    def join(self, username: str, password: str, confirm: str, email: str, code: str) -> tuple[bool, str]:
        """Plex does not support direct user creation via join.
        
        Plex uses an email-based invitation system instead of direct user creation.
        Users must be invited via email and then accept the invitation through Plex's UI.
        
        Args:
            username: Username for the new account (unused for Plex)
            password: Password for the new account (unused for Plex)
            confirm: Password confirmation (unused for Plex)
            email: Email address for the invitation
            code: Invitation code
            
        Returns:
            tuple: (False, error_message) - Plex doesn't support direct joining
        """
        return False, ("Plex does not support direct user creation. "
                      "Users must be invited via email and accept through Plex's interface. "
                      "Please use the admin panel to send Plex invitations.")
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
                # authentication token.  However, if the session provides Image tags we
                # prefer the first one marked as a *cover poster* to achieve a richer
                # artwork experience.

                artwork_url = None
                # 0) Prefer the first Image tag whose ``type`` is "coverPoster" (if any)
                images_attr = getattr(session, "image", None)
                if images_attr:
                    images_list = images_attr if isinstance(images_attr, (list, tuple, set)) else [images_attr]
                    for img in images_list:
                        if getattr(img, "type", None) == "coverPoster":
                            # Attempt to resolve an absolute URL for the image
                            img_key = getattr(img, "key", None) or getattr(img, "thumb", None)
                            if img_key:
                                artwork_url = (
                                    img_key if str(img_key).startswith("http") else self.server.url(img_key, includeToken=True)
                                )
                            elif getattr(img, "thumbUrl", None):
                                artwork_url = img.thumbUrl
                            elif getattr(img, "url", None):
                                artwork_url = img.url
                            if artwork_url:
                                break

                # 1) Fallback to more reliable poster-like attributes (already absolute path
                #    or converted to absolute):
                for attr in ("grandparentThumb", "parentThumb", "art"):
                    if artwork_url is not None:
                        break
                    val = getattr(session, attr, None)
                    if val:
                        artwork_url = val if str(val).startswith("http") else self.server.url(val, includeToken=True)

                # 2) Ultimate fallback – PlexAPI's thumbUrl (may return a frame thumbnail).
                if artwork_url is None and getattr(session, "thumbUrl", None):
                    artwork_url = session.thumbUrl
                
                # Simplified transcoding / media details -----------------------
                is_transcoding = bool(getattr(session, 'transcodeSessions', []))
                transcode_speed = None
                if is_transcoding:
                    transcode_speed = getattr(session.transcodeSessions[0], 'speed', None)

                video_codec = audio_codec = container = video_resolution = None
                if getattr(session, 'media', None):
                    media_obj = session.media[0]
                    video_codec = getattr(media_obj, 'videoCodec', None)
                    audio_codec = getattr(media_obj, 'audioCodec', None)
                    container = getattr(media_obj, 'container', None)
                    video_resolution = getattr(media_obj, 'videoResolution', None)

                transcoding_info = {
                    "is_transcoding": is_transcoding,
                    "video_codec": video_codec,
                    "audio_codec": audio_codec,
                    "container": container,
                    "video_resolution": video_resolution,
                    "transcoding_speed": transcode_speed,
                    "direct_play": not is_transcoding,
                }
                
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
                    "thumbnail_url": session.thumbUrl
                }
                
                now_playing_sessions.append(session_info)
                
            return now_playing_sessions
            
        except Exception as e:
            logging.error(f"Failed to get now playing from Plex: {e}")
            return []

    def statistics(self):
        """Return essential Plex server statistics for the dashboard.
        
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
            sessions = self.server.sessions()
            transcode_sessions = self.server.transcodeSessions()
            
            # User statistics - only what's displayed in UI
            try:
                users = self.server.myPlexAccount().users()
                stats["user_stats"] = {
                    "total_users": len(users) + 1,  # +1 for account owner
                    "active_sessions": len(sessions)
                }
            except Exception as e:
                logging.error(f"Failed to get Plex user stats: {e}")
                stats["user_stats"] = {
                    "total_users": 0,
                    "active_sessions": 0
                }
            
            # Server statistics - only version and transcoding count
            try:
                stats["server_stats"] = {
                    "version": getattr(self.server, 'version', 'Unknown'),
                    "transcoding_sessions": len(transcode_sessions)
                }
            except Exception as e:
                logging.error(f"Failed to get Plex server stats: {e}")
                stats["server_stats"] = {}
            
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


# ─── Invite & onboarding ────────────────────────────────────────────────

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

        # Use the identity linking helper for multi-server invitations
        client = PlexClient(media_server=server)
        new_user = client._create_user_with_identity_linking({
            'token': token,
            'email': email,
            'username': account.username,
            'code': code,
            'expires': expires,
            'server_id': server_id,
        })
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
            # use username as the v2 API returns only username, not e-mail
            user.acceptInvite(client.admin.username)
            user.enableViewStateSync()
            _opt_out_online_sources(user)
        except Exception as exc:
            logging.error("Post-join setup failed: %s", exc)


def _opt_out_online_sources(user: MyPlexAccount):
    for src in user.onlineMediaSources():
        src.optOut()


# ─── User queries / mutate ────────────────────────────────────────────────


