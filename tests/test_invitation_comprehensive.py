"""InvitationManager.process_invitation across one or more media servers."""

from datetime import UTC, datetime, timedelta

import pytest

from app.extensions import db
from app.models import Invitation, MediaServer, User
from app.services.expiry import calculate_user_expiry
from app.services.invitation_manager import InvitationManager
from app.services.invites import create_invite, mark_server_used


class FakeClient:
    """A media client. A successful join adds the local User, as a real one does."""

    def __init__(self, server, failure=None):
        self.server = server
        self.failure = failure

    def join(self, username, password, confirm, email, code):
        if isinstance(self.failure, Exception):
            raise self.failure
        if self.failure:
            return False, self.failure
        db.session.add(
            User(
                username=username,
                email=email,
                token=f"{username}-{self.server.id}",
                code=code,
                server_id=self.server.id,
            )
        )
        return True, ""


@pytest.fixture
def failures(monkeypatch):
    """Map a server name to the failure of its client (an error text or exception)."""
    by_name = {}
    monkeypatch.setattr(
        "app.services.invitation_manager.get_client_for_media_server",
        lambda server: FakeClient(server, by_name.get(server.name)),
    )
    return by_name


def _invitation(session, code, *server_specs):
    servers = [
        MediaServer(name=name, server_type=server_type, url="http://x", api_key="k")
        for name, server_type in server_specs
    ]
    invite = Invitation(code=code, unlimited=False)
    invite.servers = servers
    session.add(invite)
    session.commit()
    return invite, servers


def _process(code):
    return InvitationManager.process_invitation(
        code=code,
        username="testuser",
        password="testpass123",
        confirm_password="testpass123",
        email="test@example.com",
    )


def test_successful_single_server_invitation(session, failures):
    _invite, (server,) = _invitation(session, "JELLYFIN12", ("Jellyfin", "jellyfin"))

    assert _process("JELLYFIN12") == (True, "JELLYFIN12", [])

    db_user = User.query.filter_by(code="JELLYFIN12").one()
    assert db_user.username == "testuser"
    assert db_user.email == "test@example.com"
    assert db_user.server_id == server.id


def test_server_connection_failure(session, failures):
    _invitation(session, "FAIL123", ("Failing Server", "jellyfin"))
    failures["Failing Server"] = ConnectionError("Connection failed")

    assert _process("FAIL123") == (
        False,
        None,
        ["Failing Server (jellyfin): Connection failed"],
    )
    assert User.query.count() == 0


def test_multi_server_success(session, failures):
    _invite, servers = _invitation(
        session, "MULTI123", ("Jellyfin", "jellyfin"), ("Plex", "plex")
    )

    assert _process("MULTI123") == (True, "MULTI123", [])

    users = User.query.filter_by(code="MULTI123").all()
    assert sorted(user.server_id for user in users) == sorted(s.id for s in servers)


def test_multi_server_partial_failure(session, failures):
    _invite, (jellyfin, _plex) = _invitation(
        session, "PARTIAL123", ("Jellyfin", "jellyfin"), ("Plex", "plex")
    )
    failures["Plex"] = "Plex server error"

    assert _process("PARTIAL123") == (
        True,
        "PARTIAL123",
        ["Plex (plex): Plex server error"],
    )
    assert [user.server_id for user in User.query.all()] == [jellyfin.id]


def test_multi_server_complete_failure(session, failures):
    _invitation(session, "ALLFAIL123", ("Server 1", "jellyfin"), ("Server 2", "plex"))
    failures["Server 1"] = "Server 1 failed"
    failures["Server 2"] = "Server 2 failed"

    assert _process("ALLFAIL123") == (
        False,
        None,
        ["Server 1 (jellyfin): Server 1 failed", "Server 2 (plex): Server 2 failed"],
    )


@pytest.mark.parametrize(("duration", "days"), [("7", 7), ("unlimited", None)])
def test_user_expiry_follows_invitation_duration(duration, days):
    expires = calculate_user_expiry(Invitation(code="EXPIRY123", duration=duration))

    if days is None:
        assert expires is None
    else:
        expected = datetime.now(UTC) + timedelta(days=days)
        assert abs((expires - expected).total_seconds()) < 60


def test_mark_server_used_multi_server_partial(session):
    invite, (server1, _server2) = _invitation(
        session, "MULTIMARK1", ("Server 1", "jellyfin"), ("Server 2", "plex")
    )
    user = User(
        username="user1",
        email="user1@example.com",
        token="token1",
        code="MULTIMARK1",
        server_id=server1.id,
    )
    session.add(user)
    session.commit()

    mark_server_used(invite, server1.id, user)

    # A limited invitation is used only when all of its servers are used.
    session.refresh(invite)
    assert invite.used is False
    assert user in invite.users  # type: ignore


def test_mark_server_used_unlimited_multiple_users(session):
    """All users who accept an unlimited invite are recorded in invitation_users."""
    server = MediaServer(
        name="Test Server", server_type="jellyfin", url="http://x", api_key="k"
    )
    session.add(server)
    session.flush()
    invite = create_invite(
        {
            "code": "UNLIMULTI",
            "expires": "never",
            "unlimited": True,
            "server_ids": [str(server.id)],
        }
    )
    alice, bob = (
        User(
            username=name,
            email=f"{name}@example.com",
            token=f"token-{name}",
            code="UNLIMULTI",
            server_id=server.id,
        )
        for name in ("alice", "bob")
    )
    session.add_all([alice, bob])
    session.commit()

    mark_server_used(invite, server.id, alice)
    mark_server_used(invite, server.id, bob)

    session.refresh(invite)
    assert sorted(user.username for user in invite.users) == ["alice", "bob"]  # type: ignore
