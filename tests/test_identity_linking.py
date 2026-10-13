"""MediaClient._create_user_with_identity_linking and the invitation type.

A user from a limited invite gets the identity of the earlier user with the
same code (the same person on more servers). On an unlimited invite, many
people share the code. There, only a user with the same email gets the
identity of the earlier user.
"""

import pytest

from app.models import Identity, MediaServer
from app.services.invites import create_invite
from app.services.media.jellyfin import JellyfinClient


@pytest.fixture
def servers(session):
    servers = [
        MediaServer(
            name="Jellyfin Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key-1",
        ),
        MediaServer(
            name="Plex Server",
            server_type="plex",
            url="http://localhost:32400",
            api_key="test-key-2",
        ),
    ]
    session.add_all(servers)
    session.commit()
    return servers


def _invite_code(servers, unlimited):
    invitation = create_invite(
        {
            "server_ids": [str(server.id) for server in servers],
            "unlimited": unlimited,
            "expires": "never",
        }
    )
    return invitation.code


def _create_user(session, code, server, username, email):
    # The linking helper does not use the client state, so no connection is set.
    client = JellyfinClient.__new__(JellyfinClient)
    user = client._create_user_with_identity_linking(
        {
            "username": username,
            "email": email,
            "code": code,
            "server_id": server.id,
            "token": f"token-{username}",
        }
    )
    session.commit()
    return user


def _create_user_with_identity(session, code, server, username, email):
    user = _create_user(session, code, server, username, email)
    identity = Identity(primary_email=email, primary_username=username)
    session.add(identity)
    session.flush()
    user.identity_id = identity.id
    session.commit()
    return user


def test_limited_invite_users_get_linked_across_servers(session, servers):
    code = _invite_code(servers, unlimited=False)
    user1 = _create_user_with_identity(
        session, code, servers[0], "john_doe", "john@example.com"
    )

    user2 = _create_user(session, code, servers[1], "john_doe_plex", "john@example.com")

    assert user2.identity_id == user1.identity_id


def test_same_user_unlimited_invite_multiple_servers(session, servers):
    """The same person (same email) on an unlimited invite gets linked."""
    code = _invite_code(servers, unlimited=True)
    user1 = _create_user_with_identity(
        session, code, servers[0], "john_jellyfin", "john@example.com"
    )

    user2 = _create_user(session, code, servers[1], "john_plex", "john@example.com")

    assert user2.identity_id == user1.identity_id


def test_unlimited_invite_different_users_remain_separate(session, servers):
    """Different people on the same unlimited invite do not share an identity."""
    code = _invite_code(servers[:1], unlimited=True)
    user1 = _create_user_with_identity(
        session, code, servers[0], "user1", "user1@example.com"
    )

    user2 = _create_user(session, code, servers[0], "user2", "user2@example.com")

    assert user1.identity_id is not None
    assert user2.identity_id is None


@pytest.mark.parametrize("code", ["NONEXISTENT123", ""])
def test_code_without_invitation_links_nobody(session, servers, code):
    """With no invitation for the code, the user gets no identity."""
    _create_user_with_identity(session, code, servers[0], "user1", "same@example.com")

    user = _create_user(session, code, servers[1], "user2", "same@example.com")

    assert user.identity_id is None
    assert user.code == code
