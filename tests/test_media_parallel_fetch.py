"""Now playing, server health and the library scan ask servers in parallel.

Before, each of them asked the servers one after another with 60 s timeouts,
so one offline server held the dashboard (or the startup) for minutes.
"""

import threading
import time
from unittest.mock import Mock

import pytest

from app.models import Library, MediaServer, User
from app.services import library_scanner
from app.services.media import service

DELAY = 0.4


@pytest.fixture(autouse=True)
def _reset_caches():
    service.invalidate_server_caches()
    yield
    service.invalidate_server_caches()


def _servers(session, count, server_type="jellyfin"):
    servers = []
    for i in range(count):
        server = MediaServer(
            name=f"server-{i}",
            server_type=server_type,
            url=f"http://media-{i}.local",
            api_key="token",
        )
        session.add(server)
        servers.append(server)
    session.commit()
    return servers


def _slow(value, delay=DELAY):
    def call():
        time.sleep(delay)
        return value() if callable(value) else value

    return call


def _clients_by_url(monkeypatch, clients):
    """Return the fake client for each server, by server URL."""
    made = []

    def factory(server):
        client = clients[server.url]
        made.append(client)
        return client

    monkeypatch.setattr(service, "get_client_for_media_server", factory)
    return made


# ─── Now playing ────────────────────────────────────────────────────────────


def test_now_playing_cache_ttl_covers_the_dashboard_poll():
    # The dashboard polls every 10 s; a shorter TTL misses on every poll.
    assert service._NOW_PLAYING_CACHE_TTL >= 10


def test_now_playing_fetches_servers_in_parallel(session, monkeypatch):
    servers = _servers(session, 3)
    clients = {}
    for server in servers:
        client = Mock()
        client.now_playing.side_effect = _slow(
            lambda name=server.name: [{"session_id": name}]
        )
        clients[server.url] = client
    _clients_by_url(monkeypatch, clients)

    start = time.monotonic()
    sessions = service.get_now_playing_all_servers(use_cache=False)
    elapsed = time.monotonic() - start

    assert elapsed < DELAY * 2
    assert sorted(s["session_id"] for s in sessions) == [
        "server-0",
        "server-1",
        "server-2",
    ]
    for item in sessions:
        assert item["server_name"] == item["session_id"]
        assert item["server_type"] == "jellyfin"
    # Short timeouts for these calls.
    for client in clients.values():
        assert client.timeout == service.NOW_PLAYING_TIMEOUT


def test_now_playing_skips_failed_and_hung_servers(session, monkeypatch):
    servers = _servers(session, 3)
    ok, failing, hung = Mock(), Mock(), Mock()
    ok.now_playing.return_value = [{"session_id": "ok"}]
    failing.now_playing.side_effect = RuntimeError("down")
    hung.now_playing.side_effect = _slow([{"session_id": "late"}], delay=2)
    _clients_by_url(
        monkeypatch,
        {servers[0].url: ok, servers[1].url: failing, servers[2].url: hung},
    )
    monkeypatch.setattr(service, "NOW_PLAYING_DEADLINE", 0.3)

    start = time.monotonic()
    sessions = service.get_now_playing_all_servers(use_cache=False)

    assert time.monotonic() - start < 1.5
    assert [s["session_id"] for s in sessions] == ["ok"]


def test_concurrent_now_playing_callers_share_one_fetch(app, session, monkeypatch):
    (server,) = _servers(session, 1)
    client = Mock()
    client.now_playing.side_effect = _slow([{"session_id": "s1"}])
    _clients_by_url(monkeypatch, {server.url: client})
    results = []

    def caller():
        with app.app_context():
            results.append(service.get_now_playing_all_servers())

    threads = [threading.Thread(target=caller) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)

    assert client.now_playing.call_count == 1
    assert len(results) == 4
    assert all([s["session_id"] for s in r] == ["s1"] for r in results)


def test_now_playing_worker_can_read_the_db(session, monkeypatch):
    """Audiobookshelf reads local user names in now_playing(); a worker must
    have its own app context and DB session for that."""
    (server,) = _servers(session, 1)
    session.add(
        User(token="t1", username="alice", email="a@x", code="c", server_id=server.id)
    )
    session.commit()
    server_id = server.id

    class _DbClient:
        timeout = None

        def now_playing(self):
            name = User.query.filter_by(server_id=server_id).first().username
            return [{"user_name": name}]

    _clients_by_url(monkeypatch, {server.url: _DbClient()})

    sessions = service.get_now_playing_all_servers(use_cache=False)

    assert [s["user_name"] for s in sessions] == ["alice"]


# ─── Server health ──────────────────────────────────────────────────────────


def _health_client(version="10.9"):
    client = Mock()
    client.get_readonly_statistics.side_effect = _slow(
        lambda: {
            "user_stats": {"total_users": 2, "active_sessions": 0},
            "server_stats": {"version": version, "transcoding_sessions": 0},
            "library_stats": {},
            "content_stats": {},
        }
    )
    return client


def test_health_checks_servers_in_parallel_with_short_timeouts(session, monkeypatch):
    servers = _servers(session, 3)
    clients = {server.url: _health_client() for server in servers}
    _clients_by_url(monkeypatch, clients)

    start = time.monotonic()
    health = service.get_all_server_health()
    elapsed = time.monotonic() - start

    assert elapsed < DELAY * 2
    assert list(health) == [server.id for server in servers]
    for server in servers:
        stats = health[server.id]
        assert stats["server_name"] == server.name
        assert stats["server_type"] == "jellyfin"
        assert stats["server_id"] == server.id
        assert stats["server_stats"]["version"] == "10.9"
        assert "error" not in stats
    for client in clients.values():
        assert client.timeout == service.HEALTH_TIMEOUT


def test_health_results_and_failures_are_cached(session, monkeypatch):
    good, bad = _servers(session, 2)
    good_client = _health_client()
    bad_client = Mock()
    bad_client.get_readonly_statistics.side_effect = RuntimeError("offline")
    _clients_by_url(monkeypatch, {good.url: good_client, bad.url: bad_client})

    first = service.get_all_server_health()
    second = service.get_all_server_health()

    assert first == second
    assert good_client.get_readonly_statistics.call_count == 1
    # A failure is cached too, so an offline server fails fast.
    assert bad_client.get_readonly_statistics.call_count == 1
    failed = second[bad.id]
    assert failed["error"] == "Failed to get health: offline"
    assert failed["server_name"] == bad.name
    assert failed["user_stats"] == {"total_users": 0, "active_sessions": 0}
    assert failed["server_stats"] == {"version": "Unknown", "transcoding_sessions": 0}
    assert failed["library_stats"] == {}
    assert failed["content_stats"] == {}

    service.get_all_server_health(use_cache=False)
    assert good_client.get_readonly_statistics.call_count == 2


def test_health_cache_expires(session, monkeypatch):
    (server,) = _servers(session, 1)
    client = _health_client()
    _clients_by_url(monkeypatch, {server.url: client})
    monkeypatch.setattr(service, "HEALTH_CACHE_TTL", 0.0)

    service.get_all_server_health()
    service.get_all_server_health()

    assert client.get_readonly_statistics.call_count == 2


def test_health_reports_a_hung_server_as_an_error(session, monkeypatch):
    (server,) = _servers(session, 1)
    client = Mock()
    client.get_readonly_statistics.side_effect = _slow({}, delay=2)
    _clients_by_url(monkeypatch, {server.url: client})
    monkeypatch.setattr(service, "HEALTH_DEADLINE", 0.3)

    start = time.monotonic()
    health = service.get_all_server_health()

    assert time.monotonic() - start < 1.5
    assert "no answer" in health[server.id]["error"]


def test_health_route_returns_the_service_result(app, session, monkeypatch):
    (server,) = _servers(session, 1)
    _clients_by_url(monkeypatch, {server.url: _health_client()})
    expected = service.get_all_server_health()

    with app.test_request_context("/settings/servers/health/all"):
        from app.blueprints.media_servers import routes

        response = routes.get_all_health.__wrapped__()

    assert response.get_json() == {str(k): v for k, v in expected.items()}


# ─── Library scan ───────────────────────────────────────────────────────────


def _library_client(scan_result, delay=DELAY):
    client = Mock()
    client.libraries.side_effect = _slow(scan_result, delay=delay)
    client.libraries_scan_authoritative.return_value = True
    return client


def test_library_scan_runs_servers_in_parallel(session, monkeypatch):
    servers = _servers(session, 3)
    clients = {
        server.url: _library_client({f"{server.id}-1": "Movies"}) for server in servers
    }
    _clients_by_url(monkeypatch, clients)

    start = time.monotonic()
    total, errors = library_scanner.scan_all_server_libraries(show_logs=False)
    elapsed = time.monotonic() - start

    assert elapsed < DELAY * 2
    assert (total, errors) == (3, [])
    for server in servers:
        assert [lib.name for lib in Library.query.filter_by(server_id=server.id)] == [
            "Movies"
        ]
    for client in clients.values():
        assert client.timeout == (5, library_scanner.LIBRARY_SCAN_TIMEOUT)


def test_library_scan_reports_a_hung_server(session, monkeypatch):
    fast, hung = _servers(session, 2)
    _clients_by_url(
        monkeypatch,
        {
            fast.url: _library_client({"1": "Movies"}, delay=0),
            hung.url: _library_client({"2": "TV"}, delay=2),
        },
    )
    monkeypatch.setattr(library_scanner, "LIBRARY_SCAN_DEADLINE", 0.3)

    start = time.monotonic()
    total, errors = library_scanner.scan_all_server_libraries(show_logs=False)

    assert time.monotonic() - start < 1.5
    assert total == 1
    assert len(errors) == 1
    assert hung.name in errors[0]
    assert Library.query.filter_by(server_id=hung.id).count() == 0
