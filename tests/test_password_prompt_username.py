"""A mixed Plex + Jellyfin invite lets the invitee choose the username for the other servers.

The Jellyfin (and LDAP) account is created under a name the invitee has to type at
login, and Jellyfin does not accept the email address there. The Plex account name is
assigned by Plex at signup, so it is only a default - the invitee picks the final one.
"""

from unittest.mock import patch

from app.models import Invitation, MediaServer, User


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class UsernameCapturingClient:
    def __init__(self, existing=()):
        self.user_id = "jellyfin-user-1"
        self.created = []
        self.policies = []
        self.existing = [{"Name": name} for name in existing]

    def create_user(self, username, password):
        self.created.append(username)
        return self.user_id

    def get(self, endpoint):
        if endpoint == "/Users":
            return _Response(self.existing)
        return _Response({"Policy": {}})

    def set_policy(self, user_id, policy):
        self.policies.append(policy)


def _invite(session, code="PLEXUSER1", plex_username="plexh104"):
    plex = MediaServer(
        name="Plex", server_type="plex", url="http://plex.local", api_key="plex-key"
    )
    jellyfin = MediaServer(
        name="Jellyfin",
        server_type="jellyfin",
        url="http://jellyfin.local",
        api_key="jellyfin-key",
    )
    invitation = Invitation(code=code, used=False, unlimited=True)
    invitation.servers = [plex, jellyfin]
    session.add_all([plex, jellyfin, invitation])
    session.commit()

    session.add(
        User(
            username=plex_username,
            email="invitee@example.com",
            token="plex-user-token",
            code=code,
            server_id=plex.id,
        )
    )
    session.commit()
    return invitation


def _post(client, media_client, data):
    with patch(
        "app.services.media.service.get_client_for_media_server",
        return_value=media_client,
    ):
        return client.post("/j/PLEXUSER1/password", data=data)


def test_invitee_can_pick_the_username_for_the_other_servers(client, session):
    _invite(session)
    media_client = UsernameCapturingClient()

    response = _post(
        client,
        media_client,
        {"username": "joey", "password": "password123", "confirm": "password123"},
    )

    assert response.status_code == 302
    assert media_client.created == ["joey"]


def test_plex_username_stays_the_default_when_none_is_given(client, session):
    _invite(session)
    media_client = UsernameCapturingClient()

    response = _post(
        client, media_client, {"password": "password123", "confirm": "password123"}
    )

    assert response.status_code == 302
    assert media_client.created == ["plexh104"]


def test_username_with_spaces_is_rejected(client, session):
    _invite(session)
    media_client = UsernameCapturingClient()

    response = _post(
        client,
        media_client,
        {"username": "bad user", "password": "password123", "confirm": "password123"},
    )

    assert response.status_code == 200
    assert media_client.created == []
    assert b"Username can contain letters" in response.data


def test_the_form_shows_the_default_username(client, session):
    _invite(session)

    response = client.get("/j/PLEXUSER1/password")

    assert response.status_code == 200
    assert b'name="username"' in response.data
    assert b'value="plexh104"' in response.data


def test_username_already_taken_is_rejected_before_anything_is_created(client, session):
    _invite(session)
    media_client = UsernameCapturingClient(existing=["joey"])

    response = _post(
        client,
        media_client,
        {"username": "Joey", "password": "password123", "confirm": "password123"},
    )

    assert response.status_code == 200
    assert media_client.created == []
    assert b"already taken" in response.data


def test_an_existing_default_name_is_reported_too(client, session):
    """The common case: the invitee leaves the field alone and the name exists.

    That is exactly the silent failure this guards against - previously the
    create_user error was only logged and the invite still claimed success.
    """
    _invite(session)
    media_client = UsernameCapturingClient(existing=["plexh104"])

    response = _post(
        client, media_client, {"password": "password123", "confirm": "password123"}
    )

    assert response.status_code == 200
    assert media_client.created == []
    assert b"already taken" in response.data
