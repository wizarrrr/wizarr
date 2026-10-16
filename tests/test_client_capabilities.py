"""
Server types declare what they support in ClientCapabilities on their client,
and the code that used to keep its own lists of server types asks the
registry instead. The declarations must reproduce the old behaviour exactly.
"""

from typing import ClassVar

import pytest

from app.extensions import db
from app.models import Invitation, MediaServer
from app.services.expiry import server_supports_disable
from app.services.invitation_flow.strategies import FormBasedStrategy
from app.services.media.client_base import (
    CLIENTS,
    ClientCapabilities,
    MediaClient,
    join_fields_for,
)

# get_server_disable_capabilities() as it stood before capabilities existed
OLD_DISABLE_MAP = {
    "jellyfin": True,
    "emby": True,
    "plex": False,
    "audiobookshelf": True,
    "kavita": True,
    "komga": True,
    "romm": True,
    "navidrome": False,
    "drop": False,
}


@pytest.mark.parametrize(("server_type", "expected"), OLD_DISABLE_MAP.items())
def test_disable_matches_the_old_map(server_type, expected):
    assert server_supports_disable(server_type) is expected


def test_unknown_type_is_delete_only():
    assert server_supports_disable("no-such-type") is False


def test_every_client_declares_capabilities():
    for name, client in CLIENTS.items():
        assert isinstance(client.capabilities, ClientCapabilities), name


def test_existing_clients_keep_the_full_join_form():
    for server_type in OLD_DISABLE_MAP:
        assert join_fields_for([server_type]) == ["username", "email", "password"]


class EmailOnlyClient(MediaClient):
    """A test-only client that asks the invitee for an address and nothing else."""

    capabilities = ClientCapabilities(join_fields=("email",))
    joined: ClassVar[list[tuple[str, str]]] = []

    def __init__(self, *args, **kwargs):
        self.url = "http://email-only.local"
        self.token = "token"

    def _do_join(self, username, password, confirm, email, code):
        EmailOnlyClient.joined.append((email, code))
        return True, ""

    def libraries(self):
        return {}

    def scan_libraries(self, url=None, token=None):
        return {}

    def create_user(self, *args, **kwargs):
        return ""

    def update_user(self, *args, **kwargs):
        return {}

    def enable_user(self, user_id):
        return True

    def disable_user(self, user_id):
        return True

    def delete_user(self, *args, **kwargs):
        return None

    def get_user(self, *args, **kwargs):
        return {}

    def list_users(self, *args, **kwargs):
        return []

    def now_playing(self):
        return []

    def statistics(self):
        return {}


@pytest.fixture
def email_only(monkeypatch):
    monkeypatch.setitem(CLIENTS, "email_only", EmailOnlyClient)
    monkeypatch.setattr(EmailOnlyClient, "joined", [])
    monkeypatch.setattr(
        "app.services.media.service.get_client_for_media_server",
        lambda server: CLIENTS[server.server_type](media_server=server),
    )
    monkeypatch.setattr(
        "app.services.invitation_flow.workflows.get_client_for_media_server",
        lambda server: CLIENTS[server.server_type](media_server=server),
    )
    return EmailOnlyClient


def test_join_fields_union_and_order(email_only):
    assert join_fields_for(["email_only"]) == ["email"]
    assert join_fields_for(["email_only", "jellyfin"]) == [
        "username",
        "email",
        "password",
    ]
    assert join_fields_for([]) == ["username", "email", "password"]
    assert join_fields_for(["no-such-type"]) == ["username", "email", "password"]


def test_strategy_requires_only_the_declared_fields(email_only):
    server = MediaServer(name="E", server_type="email_only", url="http://e")
    ok, _msg, _data = FormBasedStrategy().authenticate(
        [server], {"email": "reader@example.com"}
    )
    assert ok is True


def test_strategy_still_checks_passwords_for_full_form_servers():
    server = MediaServer(name="J", server_type="jellyfin", url="http://j")
    ok, msg, _data = FormBasedStrategy().authenticate(
        [server],
        {
            "username": "reader",
            "email": "reader@example.com",
            "password": "Password1",
            "confirm_password": "Different1",
        },
    )
    assert ok is False
    assert "Passwords do not match" in msg


def _invite(server_type, code):
    server = MediaServer(name="S", server_type=server_type, url="http://s", api_key="k")
    invitation = Invitation(code=code, used=False, unlimited=True)
    invitation.servers.append(server)
    db.session.add_all([server, invitation])
    db.session.commit()
    return server


def test_email_only_invite_page_and_submission(client, session, email_only):
    _invite("email_only", "EMAILONLY1")

    body = client.get("/j/EMAILONLY1").get_data(as_text=True)
    assert 'name="email"' in body
    assert 'name="username"' not in body
    assert 'name="password"' not in body

    client.post(
        "/invitation/process",
        data={"code": "EMAILONLY1", "email": "reader@example.com"},
    )
    assert email_only.joined == [("reader@example.com", "EMAILONLY1")]


def test_full_form_servers_still_show_every_field(client, session):
    _invite("jellyfin", "JELLYFORM1")

    body = client.get("/j/JELLYFORM1").get_data(as_text=True)
    for field in ("username", "email", "password", "confirm_password"):
        assert f'name="{field}"' in body
