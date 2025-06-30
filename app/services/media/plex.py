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
    if inv.libraries:
        libs = [lib.external_id for lib in inv.libraries]
    else:
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


