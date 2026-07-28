"""An empty remote user list must not delete every local user.

list_users() runs automatically when the Users page loads (admin/users.html has a
hidden hx-get with hx-trigger="load"). It guards against the request raising, but
a successful response that yields no users was treated as "the admin unshared
everyone" and pruned every local row.
"""

from unittest.mock import Mock, PropertyMock, patch

import pytest

from app.models import MediaServer, User
from app.services.media.audiobookshelf import AudiobookshelfClient
from app.services.media.drop import DropClient
from app.services.media.emby import EmbyClient
from app.services.media.jellyfin import JellyfinClient
from app.services.media.kavita import KavitaClient
from app.services.media.komga import KomgaClient
from app.services.media.navidrome import NavidromeClient
from app.services.media.plex import PlexClient
from app.services.media.romm import RommClient


def _server(session):
    server = MediaServer(
        name="Plex", server_type="plex", url="http://plex.local", api_key="token"
    )
    session.add(server)
    session.commit()
    return server


def _users(session, server, emails):
    for email in emails:
        session.add(
            User(
                email=email,
                username=email.split("@")[0],
                token="None",
                code="None",
                server_id=server.id,
            )
        )
    session.commit()


def _client(server):
    """Build a PlexClient without touching the network."""
    client = PlexClient.__new__(PlexClient)
    client.server_id = server.id
    return client


def _emails(server):
    return {u.email for u in User.query.filter_by(server_id=server.id).all()}


def test_empty_remote_list_does_not_delete_local_users(session):
    """The reported failure: a successful response with zero users wiped the table."""
    server = _server(session)
    _users(session, server, ["a@example.com", "b@example.com"])
    client = _client(server)

    # spec'd deliberately: a bare Mock auto-creates any attribute, which hides
    # typos like self.server.name (PlexServer exposes friendlyName, not name)
    fake_server = Mock(spec=["machineIdentifier", "friendlyName"])
    fake_server.machineIdentifier = "mid"
    with (
        patch.object(PlexClient, "admin", new_callable=PropertyMock) as admin,
        patch.object(PlexClient, "server", new_callable=PropertyMock) as srv,
        patch.object(PlexClient, "_filter_users_for_server", return_value={}),
    ):
        admin.return_value.users.return_value = []
        srv.return_value = fake_server
        PlexClient.list_users.__wrapped__(client)

    assert _emails(server) == {"a@example.com", "b@example.com"}


def test_genuine_removal_still_prunes(session):
    """A non-empty remote set must still drop users that are no longer shared."""
    server = _server(session)
    _users(session, server, ["keep@example.com", "gone@example.com"])
    client = _client(server)

    # spec'd deliberately: a bare Mock auto-creates any attribute, which hides
    # typos like self.server.name (PlexServer exposes friendlyName, not name)
    fake_server = Mock(spec=["machineIdentifier", "friendlyName"])
    fake_server.machineIdentifier = "mid"
    keeper = Mock(title="keep")
    with (
        patch.object(PlexClient, "admin", new_callable=PropertyMock) as admin,
        patch.object(PlexClient, "server", new_callable=PropertyMock) as srv,
        patch.object(
            PlexClient,
            "_filter_users_for_server",
            return_value={"keep@example.com": keeper},
        ),
        patch.object(PlexClient, "_sync_user_permissions", return_value=None),
    ):
        admin.return_value.users.return_value = [keeper]
        srv.return_value = fake_server
        PlexClient.list_users.__wrapped__(client)

    assert _emails(server) == {"keep@example.com"}


# ─── The same bug was latent in every other backend ─────────────────────────
#
# They all share one shape: build a dict of remote users, then prune every local
# user whose key is absent from it. A successful-but-empty fetch made that dict
# empty and deleted everyone. The base-class guard (_skip_prune_on_empty_remote)
# now covers them all; these tests drive each real list_users with an empty
# remote set and assert the local rows survive.


class _EmptyResp:
    """A successful HTTP response whose body is an empty user list."""

    status_code = 200
    text = "[]"

    def json(self):
        return []

    def raise_for_status(self):
        return None


def _make_server(session, server_type):
    server = MediaServer(
        name=server_type,
        server_type=server_type,
        url="http://media.local",
        api_key="token",
    )
    session.add(server)
    session.commit()
    return server


def _seed(session, server, names):
    for name in names:
        session.add(
            User(
                token=name,
                username=name,
                email=f"{name}@example.com",
                code="empty",
                server_id=server.id,
            )
        )
    session.commit()


def _rest_client(cls, server):
    """Build a client without running __init__ (no network/credentials)."""
    client = cls.__new__(cls)
    client.server_id = server.id
    return client


def _usernames(server):
    return {u.username for u in User.query.filter_by(server_id=server.id).all()}


@pytest.mark.parametrize(
    ("cls", "server_type"),
    [
        (JellyfinClient, "jellyfin"),
        (EmbyClient, "emby"),
        (AudiobookshelfClient, "audiobookshelf"),
        (KomgaClient, "komga"),
        (KavitaClient, "kavita"),
        (RommClient, "romm"),
        (DropClient, "drop"),
    ],
)
def test_empty_remote_preserves_local_users(session, cls, server_type):
    """A successful but empty user fetch must not wipe the local rows."""
    server = _make_server(session, server_type)
    _seed(session, server, ["alice", "bob"])
    client = _rest_client(cls, server)
    client.get = lambda *args, **kwargs: _EmptyResp()

    client.list_users()

    assert _usernames(server) == {"alice", "bob"}


def test_empty_remote_preserves_local_users_navidrome(session):
    """Navidrome fetches over Subsonic rather than .get(), but the guard still applies."""
    server = _make_server(session, "navidrome")
    _seed(session, server, ["alice", "bob"])
    client = _rest_client(NavidromeClient, server)

    with patch.object(
        NavidromeClient, "_subsonic_request", return_value={"users": {"user": []}}
    ):
        client.list_users()

    assert _usernames(server) == {"alice", "bob"}


def test_skip_prune_helper_decision(session):
    """The guard skips only when the remote set is empty AND local users exist."""
    server = _make_server(session, "jellyfin")
    client = _rest_client(JellyfinClient, server)
    present = [Mock()]

    assert client._skip_prune_on_empty_remote(True, present) is True
    assert client._skip_prune_on_empty_remote(False, present) is False
    assert client._skip_prune_on_empty_remote(True, []) is False
