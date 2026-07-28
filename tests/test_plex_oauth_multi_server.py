from app.extensions import db
from app.models import Invitation, MediaServer, User, invitation_servers
from app.services.media import plex as plex_service


class FakePlexAccount:
    email = "viewer@example.com"
    username = "viewer"

    def __init__(self, token):
        self.token = token


class FakePlexClient:
    def __init__(self, media_server):
        self.media_server = media_server
        self.url = media_server.url
        self.token = media_server.api_key

    def _create_user_with_identity_linking(self, user_data):
        user = User(
            token=user_data["token"],
            username=user_data["username"],
            email=user_data["email"],
            code=user_data["code"],
            server_id=user_data["server_id"],
            expires=user_data["expires"],
        )
        db.session.add(user)
        db.session.flush()
        return user


class ImmediateThread:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass


def test_plex_oauth_invites_every_plex_server_on_multi_server_invite(
    app, session, monkeypatch
):
    plex_primary = MediaServer(
        name="Plex Primary",
        server_type="plex",
        url="http://plex-primary:32400",
        api_key="primary-token",
    )
    plex_secondary = MediaServer(
        name="Plex Secondary",
        server_type="plex",
        url="http://plex-secondary:32400",
        api_key="secondary-token",
    )
    emby = MediaServer(
        name="Emby",
        server_type="emby",
        url="http://emby:8096",
        api_key="emby-token",
    )
    invitation = Invitation(code="MULTIPLEX", unlimited=False)
    invitation.servers.extend([plex_primary, plex_secondary, emby])
    session.add(invitation)
    session.commit()

    invited_server_ids = []

    def fake_invite_user(email, code, user_id, server):
        invited_server_ids.append(server.id)

    monkeypatch.setattr(plex_service, "MyPlexAccount", FakePlexAccount)
    monkeypatch.setattr(plex_service, "PlexClient", FakePlexClient)
    monkeypatch.setattr(plex_service, "_invite_user", fake_invite_user)
    monkeypatch.setattr(plex_service, "_post_join_setup", lambda *args: None)
    monkeypatch.setattr(plex_service.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(plex_service, "notify", lambda *args, **kwargs: None)

    plex_service.handle_oauth_token(app, "oauth-token", invitation.code)

    users = User.query.filter_by(email="viewer@example.com").all()
    assert {user.server_id for user in users} == {plex_primary.id, plex_secondary.id}
    assert invited_server_ids == [plex_primary.id, plex_secondary.id]

    usage_rows = session.execute(
        invitation_servers.select().where(
            invitation_servers.c.invite_id == invitation.id
        )
    ).all()
    usage_by_server = {row.server_id: row.used for row in usage_rows}
    assert usage_by_server == {
        plex_primary.id: True,
        plex_secondary.id: True,
        emby.id: False,
    }
