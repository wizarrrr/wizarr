"""Plex statistics do not sync users, and Plex checks have a connect timeout.

PlexClient.statistics() called list_users(). That is a full plex.tv sync with
database writes, on each statistics request. It now counts the users in the
database.

check_plex() and the /plex/scan helper built PlexServer() with no timeout, so
an offline host held the request for a long time.

All Plex calls go to fakes. No test uses the network.
"""

from types import SimpleNamespace

import pytest

from app.blueprints.plex import routes as plex_routes
from app.extensions import db
from app.models import MediaServer, User
from app.services import servers as servers_module
from app.services.media.plex import PlexClient
from app.services.servers import PLEX_CHECK_TIMEOUT, check_plex

pytestmark = pytest.mark.usefixtures("clear_media_caches")


class _FakePlexServer:
    version = "1.40"

    def __init__(self, sessions=(), transcodes=()):
        self._sessions = list(sessions)
        self._transcodes = list(transcodes)

    def sessions(self):
        return self._sessions

    def transcodeSessions(self):
        return self._transcodes


def test_statistics_counts_users_from_the_database(app, session, monkeypatch):
    with app.app_context():
        server = MediaServer(
            name="Plex", server_type="plex", url="http://plex.local", api_key="k"
        )
        db.session.add(server)
        db.session.commit()
        for i in range(3):
            db.session.add(
                User(
                    token=f"t{i}",
                    username=f"user{i}",
                    email=f"user{i}@example.com",
                    code=f"C{i}",
                    server_id=server.id,
                )
            )
        db.session.commit()

        def no_sync(*_args, **_kwargs):
            raise AssertionError("statistics() must not sync users")

        monkeypatch.setattr(PlexClient, "list_users", no_sync)
        client = PlexClient(media_server=server)
        client._server = _FakePlexServer(sessions=[object()], transcodes=[object()])

        stats = client.statistics()

    assert stats["user_stats"] == {"total_users": 3, "active_sessions": 1}
    assert stats["server_stats"] == {"version": "1.40", "transcoding_sessions": 1}
    assert set(stats) == {
        "library_stats",
        "user_stats",
        "server_stats",
        "content_stats",
    }


def test_check_plex_uses_a_connect_timeout(monkeypatch):
    calls = []

    def fake_plex_server(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace()

    monkeypatch.setattr(servers_module, "PlexServer", fake_plex_server)

    assert check_plex("http://plex.local", "tok") == (True, "")
    ((args, kwargs),) = calls
    assert args == ("http://plex.local",)
    assert kwargs == {"token": "tok", "timeout": PLEX_CHECK_TIMEOUT}
    connect_timeout, _read_timeout = PLEX_CHECK_TIMEOUT
    assert connect_timeout <= 5


def test_plex_scan_uses_a_connect_timeout(monkeypatch):
    calls = []

    def fake_plex_server(*args, **kwargs):
        calls.append((args, kwargs))
        section = SimpleNamespace(title="Movies")
        return SimpleNamespace(library=SimpleNamespace(sections=lambda: [section]))

    monkeypatch.setattr("plexapi.server.PlexServer", fake_plex_server)

    # _scan keeps results for 5 minutes, so use a URL that no other test uses.
    assert plex_routes._scan("http://scan-timeout.local", "tok") == ["Movies"]
    ((args, kwargs),) = calls
    assert args == ("http://scan-timeout.local", "tok")
    assert kwargs == {"timeout": PLEX_CHECK_TIMEOUT}
