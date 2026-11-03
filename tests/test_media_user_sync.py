"""User sync: fewer DB queries, and a throttled sync for each server.

Before, each client queried ``User`` once for each remote user (and Jellyfin
and Audiobookshelf queried ``Library`` once for each folder of each user), and
every Users page visit and every ``GET /api/users`` ran a full live sync of
every server.
"""

import hashlib
import threading
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import event

from app.extensions import db
from app.models import ApiKey, Library, MediaServer, User
from app.services.media import service
from app.services.media.audiobookshelf import AudiobookshelfClient
from app.services.media.drop import DropClient
from app.services.media.jellyfin import JellyfinClient
from app.services.media.kavita import KavitaClient
from app.services.media.komga import KomgaClient
from app.services.media.navidrome import NavidromeClient
from app.services.media.romm import RommClient


@pytest.fixture(autouse=True)
def _reset_sync_state():
    service.invalidate_server_caches()
    yield
    service.invalidate_server_caches()


@contextmanager
def count_selects():
    """Count the SELECT statements sent to the DB in the block."""
    counter = {"selects": 0}

    def _before(_conn, _cursor, statement, *_args):
        if statement.lstrip().upper().startswith("SELECT"):
            counter["selects"] += 1

    engine = db.engine
    event.listen(engine, "before_cursor_execute", _before)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", _before)


class _Resp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload
        self.text = "[...]"

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def _server(session, server_type, name=None):
    server = MediaServer(
        name=name or server_type,
        server_type=server_type,
        url=f"http://{server_type}.local",
        api_key="token",
    )
    session.add(server)
    session.commit()
    return server


def _seed_users(session, server, tokens):
    for token in tokens:
        session.add(
            User(
                token=token,
                username=token,
                email=f"{token}@example.com",
                code="empty",
                server_id=server.id,
            )
        )
    session.commit()


def _seed_libraries(session, server, ids):
    for lib_id in ids:
        session.add(
            Library(external_id=lib_id, name=f"Lib {lib_id}", server_id=server.id)
        )
    session.commit()


def _client(cls, server):
    client = cls.__new__(cls)
    client.server_id = server.id
    client.url = server.url
    client.token = server.api_key
    return client


def _clear_users(session):
    session.query(User).delete()
    session.commit()


# ─── Fewer queries ──────────────────────────────────────────────────────────


def _jellyfin_users(count):
    return [
        {
            "Id": f"jf-{i}",
            "Name": f"user{i}",
            "Policy": {"EnableAllFolders": False, "EnabledFolders": ["a", "b"]},
        }
        for i in range(count)
    ]


def _run_jellyfin_sync(session, server, remote_count):
    _clear_users(session)
    # Half of the remote users exist locally, plus one user that is gone.
    _seed_users(session, server, [f"jf-{i}" for i in range(remote_count // 2)])
    _seed_users(session, server, ["jf-gone"])
    client = _client(JellyfinClient, server)
    remote = _jellyfin_users(remote_count)
    client.get = lambda *_a, **_kw: _Resp(remote)
    with count_selects() as counter:
        users = client.list_users()
    return counter["selects"], users


def test_jellyfin_sync_query_count_does_not_grow_with_users(session):
    server = _server(session, "jellyfin")
    _seed_libraries(session, server, ["a", "b", "c"])

    small, _ = _run_jellyfin_sync(session, server, 4)
    large, users = _run_jellyfin_sync(session, server, 40)

    assert large == small
    assert len(users) == 40
    assert {u.token for u in users} == {f"jf-{i}" for i in range(40)}
    for user in users:
        assert user.get_accessible_libraries() == ["Lib a", "Lib b"]


def test_audiobookshelf_sync_query_count_does_not_grow_with_users(session):
    server = _server(session, "audiobookshelf")
    _seed_libraries(session, server, ["a", "b"])

    def run(count):
        _clear_users(session)
        _seed_users(session, server, [f"abs-{i}" for i in range(count // 2)])
        client = _client(AudiobookshelfClient, server)
        remote = [
            {"id": f"abs-{i}", "username": f"u{i}", "librariesAccessible": ["a"]}
            for i in range(count)
        ]
        client.get = lambda *_a, **_kw: _Resp(remote)
        with count_selects() as counter:
            users = client.list_users()
        return counter["selects"], users

    small, _ = run(4)
    large, users = run(40)

    assert large == small
    assert len(users) == 40
    assert all(u.get_accessible_libraries() == ["Lib a"] for u in users)


@pytest.mark.parametrize(
    ("cls", "server_type", "make_remote"),
    [
        (KavitaClient, "kavita", lambda i: {"id": i, "username": f"u{i}"}),
        (RommClient, "romm", lambda i: {"id": i, "username": f"u{i}"}),
        (DropClient, "drop", lambda i: {"id": i, "username": f"u{i}"}),
    ],
)
def test_basic_clients_sync_query_count_does_not_grow(
    session, cls, server_type, make_remote
):
    server = _server(session, server_type)

    def run(count):
        _clear_users(session)
        # Ids start at 1: Drop skips a falsy id.
        _seed_users(session, server, [str(i) for i in range(1, count // 2 + 1)])
        client = _client(cls, server)
        remote = [make_remote(i) for i in range(1, count + 1)]

        def fake_get(*_a, **_kw):
            return _Resp(remote)

        client.get = fake_get
        with count_selects() as counter:
            client.list_users()
        return counter["selects"]

    small = run(4)
    large = run(40)

    assert large == small
    assert {u.token for u in User.query.filter_by(server_id=server.id).all()} == {
        str(i) for i in range(1, 41)
    }


def test_navidrome_sync_query_count_does_not_grow(session):
    server = _server(session, "navidrome")

    def run(count):
        _clear_users(session)
        _seed_users(session, server, [f"n{i}" for i in range(count // 2)])
        client = _client(NavidromeClient, server)
        remote = [{"id": f"nid-{i}", "userName": f"n{i}"} for i in range(count)]
        with (
            patch.object(NavidromeClient, "_native_users", return_value=remote),
            count_selects() as counter,
        ):
            client.list_users()
        return counter["selects"]

    small = run(4)
    large = run(40)

    assert large == small
    assert len(User.query.filter_by(server_id=server.id).all()) == 40


def test_komga_sync_fetches_libraries_once(session):
    server = _server(session, "komga")
    _seed_libraries(session, server, ["a", "b"])

    def run(count):
        _clear_users(session)
        _seed_users(session, server, [f"k{i}" for i in range(count // 2)])
        client = _client(KomgaClient, server)
        remote = [
            {
                "id": f"k{i}",
                "email": f"k{i}@example.com",
                "roles": ["FILE_DOWNLOAD"],
                "sharedAllLibraries": True,
            }
            for i in range(count)
        ]
        client.get = lambda *_a, **_kw: _Resp(remote)
        client.libraries = Mock(return_value={"a": "Lib a", "b": "Lib b"})
        with count_selects() as counter:
            users = client.list_users()
        return counter["selects"], client.libraries.call_count, users

    small, _, _ = run(4)
    large, library_calls, users = run(20)

    assert large == small
    # Before, the remote library list was fetched once per user.
    assert library_calls == 1
    assert all(u.get_accessible_libraries() == ["Lib a", "Lib b"] for u in users)


def test_kavita_sync_matches_tokens_on_this_server_only(session):
    """A user with the same id on another server must not block this one."""
    other = _server(session, "kavita", name="other")
    _seed_users(session, other, ["1"])
    server = _server(session, "kavita", name="this")
    client = _client(KavitaClient, server)
    client.get = lambda *_a, **_kw: _Resp([{"id": 1, "username": "alice"}])

    client.list_users()

    assert [u.username for u in User.query.filter_by(server_id=server.id)] == ["alice"]
    assert User.query.filter_by(server_id=other.id).count() == 1


# ─── Throttled sync ─────────────────────────────────────────────────────────


@pytest.fixture
def fake_client(monkeypatch):
    client = Mock()
    client.list_users.return_value = []
    client.remote_errors = 0
    monkeypatch.setattr(service, "get_client_for_media_server", lambda _s: client)
    return client


def test_sync_runs_once_within_max_age(session, fake_client):
    _server(session, "jellyfin")

    assert service.sync_users() is True
    assert service.sync_users() is False
    assert fake_client.list_users.call_count == 1

    assert service.sync_users(force=True) is True
    assert service.sync_users(max_age=0) is True
    assert fake_client.list_users.call_count == 3


def test_sync_of_one_server_leaves_the_other(session, fake_client):
    first = _server(session, "jellyfin", name="first")
    _server(session, "emby", name="second")

    assert service.sync_users(first) is True
    assert fake_client.list_users.call_count == 1

    # Only the second server is still stale.
    assert service.sync_users() is True
    assert fake_client.list_users.call_count == 2
    assert service.sync_users() is False


def test_auto_link_runs_only_when_a_sync_ran(session, fake_client, monkeypatch):
    _server(session, "jellyfin")
    auto_link = Mock()
    monkeypatch.setattr(service, "_auto_link_identities", auto_link)

    service.sync_users()
    service.sync_users()

    auto_link.assert_called_once()


def test_changed_server_url_makes_the_sync_stale(session, fake_client):
    server = _server(session, "jellyfin")
    service.sync_users()

    server.url = "http://new-host.local"
    session.commit()

    assert service.sync_users() is True
    assert fake_client.list_users.call_count == 2


def test_invalidate_makes_the_sync_run(session, fake_client):
    server = _server(session, "jellyfin")
    service.sync_users()

    service.invalidate_server_caches(server.id)

    assert service.sync_users() is True


def test_failed_sync_is_not_recorded(session, fake_client):
    _server(session, "jellyfin")
    fake_client.list_users.side_effect = RuntimeError("down")

    assert service.sync_users() is False

    fake_client.list_users.side_effect = None
    assert service.sync_users() is True


def test_list_users_for_server_counts_as_a_sync(session, fake_client):
    server = _server(session, "jellyfin")

    service.list_users_for_server(server)

    assert service.sync_users() is False
    assert fake_client.list_users.call_count == 1


class _SpyLock:
    """Wrap a lock and report when the second caller is about to wait on it."""

    def __init__(self, lock, waiting):
        self._lock = lock
        self._waiting = waiting

    def __enter__(self):
        if threading.current_thread().name == "second":
            self._waiting.set()
        return self._lock.__enter__()

    def __exit__(self, *exc):
        return self._lock.__exit__(*exc)


@pytest.mark.parametrize("force", [False, True])
def test_concurrent_callers_sync_a_server_once(
    app, session, fake_client, monkeypatch, force
):
    _server(session, "jellyfin")
    started = threading.Event()
    release = threading.Event()
    second_waiting = threading.Event()

    real_lock_for = service._user_sync_lock
    monkeypatch.setattr(
        service,
        "_user_sync_lock",
        lambda server_id: _SpyLock(real_lock_for(server_id), second_waiting),
    )

    def slow_list_users():
        started.set()
        assert release.wait(5)
        return []

    fake_client.list_users.side_effect = slow_list_users
    results = []

    def caller():
        with app.app_context():
            results.append(service.sync_users(force=force))

    first = threading.Thread(target=caller, name="first")
    first.start()
    assert started.wait(5)
    # The second caller asks while the first sync still runs.
    second = threading.Thread(target=caller, name="second")
    second.start()
    assert second_waiting.wait(5)
    release.set()
    first.join(5)
    second.join(5)

    assert fake_client.list_users.call_count == 1
    assert sorted(results) == [False, True]


# ─── GET /api/users ─────────────────────────────────────────────────────────


@pytest.fixture
def api_key(session, admin_user):
    raw_key = "sync_test_api_key"
    session.add(
        ApiKey(
            name="Sync test key",
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            created_by_id=admin_user.id,
            is_active=True,
        )
    )
    session.commit()
    return raw_key


def test_api_users_uses_the_throttled_sync(client, session, api_key, fake_client):
    server = _server(session, "jellyfin")
    _seed_users(session, server, ["alice", "bob"])
    headers = {"X-API-Key": api_key}

    first = client.get("/api/users", headers=headers)
    second = client.get("/api/users?username=bob", headers=headers)

    assert first.status_code == 200
    assert {u["username"] for u in first.get_json()["users"]} == {"alice", "bob"}
    assert [u["username"] for u in second.get_json()["users"]] == ["bob"]
    assert second.get_json()["users"][0]["server"] == "jellyfin"
    # The second call is inside USER_SYNC_MAX_AGE, so no remote sync.
    assert fake_client.list_users.call_count == 1


def test_api_users_serves_stored_users_when_sync_fails(
    client, session, api_key, fake_client
):
    server = _server(session, "jellyfin")
    _seed_users(session, server, ["alice"])
    fake_client.list_users.side_effect = RuntimeError("server down")

    response = client.get("/api/users", headers={"X-API-Key": api_key})

    assert response.status_code == 200
    assert [u["username"] for u in response.get_json()["users"]] == ["alice"]


def test_sync_with_remote_errors_is_not_recorded(session, fake_client):
    # A client that catches a remote error returns the stored users. The
    # throttle must not count that call as a successful sync.
    _server(session, "jellyfin")

    def failing_list_users():
        fake_client.remote_errors += 1
        return []

    fake_client.list_users.side_effect = failing_list_users

    assert service.sync_users() is True
    assert service.sync_users() is True
    assert fake_client.list_users.call_count == 2


def test_rest_request_failure_counts_a_remote_error(monkeypatch):
    from app.services.media import client_base
    from app.services.media.jellyfin import JellyfinClient

    client = JellyfinClient.__new__(JellyfinClient)
    client.url = "http://jellyfin.invalid"
    client.token = "key"

    session = Mock()
    session.request.side_effect = client_base.requests.ConnectionError("down")
    monkeypatch.setattr(client_base, "get_http_session", lambda: session)

    with pytest.raises(client_base.requests.ConnectionError):
        client.get("/Users")

    assert client.remote_errors == 1
    assert JellyfinClient.remote_errors == 0
