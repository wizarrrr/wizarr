"""Plex client: fewer remote calls, shared connections and small images.

All network calls are fakes. The tests count the calls that the Plex client
makes, so a change that adds calls for each user or each request fails here.
"""

import gc
import json
import re
import weakref
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import Mock
from urllib.parse import parse_qs, unquote_plus, urlsplit

import pytest
import requests
from plexapi import TIMEOUT as PLEXAPI_TIMEOUT
from plexapi.exceptions import NotFound
from plexapi.server import PlexServer
from sqlalchemy import event

from app.extensions import db
from app.models import MediaServer, User
from app.services.image_proxy import ImageProxyService
from app.services.media import plex as plex_module
from app.services.media.client_base import get_http_session
from app.services.media.plex import PlexClient

pytestmark = pytest.mark.usefixtures("clear_media_caches")

MACHINE_ID = "machine-1"
ADMIN_TOKEN = "plex-admin-token"  # test fixture, not a real credential


class FakePlexServer:
    """Enough of PlexServer for these tests. URLs use the real plexapi code."""

    _cached_data_properties: ClassVar[set[str]] = {"library"}
    url = PlexServer.url
    transcodeImage = PlexServer.transcodeImage

    def __init__(self, baseurl, token, session=None, timeout=None):
        self._baseurl = baseurl.rstrip("/")
        self._token = token
        self._showSecrets = False
        self._session = session
        self._timeout = timeout
        self.machineIdentifier = MACHINE_ID
        self.friendlyName = "Plex"
        self.version = "1.40"
        self.transcoderPhoto = True
        self.session_list = []

    def sessions(self):
        return self.session_list

    def transcodeSessions(self):
        return []


def _row(url="http://plex.local:32400", token=ADMIN_TOKEN, server_id=1):
    return SimpleNamespace(id=server_id, url=url, api_key=token)


def _count_constructions(monkeypatch, attr, factory):
    built = []

    def build(*args, **kwargs):
        built.append((args, kwargs))
        return factory(*args, **kwargs)

    monkeypatch.setattr(plex_module, attr, build)
    return built


# ─── Shared connections ─────────────────────────────────────────────────────


def test_clients_share_one_server_connection(monkeypatch):
    built = _count_constructions(monkeypatch, "PlexServer", FakePlexServer)

    first = PlexClient(media_server=_row()).server
    second = PlexClient(media_server=_row()).server

    assert first is second
    assert len(built) == 1
    _args, kwargs = built[0]
    assert kwargs["session"] is get_http_session()
    assert kwargs["timeout"] == (5, PLEXAPI_TIMEOUT)


def test_clients_share_one_account(monkeypatch):
    built = _count_constructions(
        monkeypatch, "MyPlexAccount", lambda **kwargs: SimpleNamespace(**kwargs)
    )

    first = PlexClient(media_server=_row()).admin
    second = PlexClient(media_server=_row()).admin

    assert first is second
    assert len(built) == 1
    _args, kwargs = built[0]
    assert kwargs["token"] == ADMIN_TOKEN
    assert kwargs["session"] is get_http_session()


def test_other_url_or_token_gets_its_own_connection(monkeypatch):
    built = _count_constructions(monkeypatch, "PlexServer", FakePlexServer)

    servers = {
        PlexClient(media_server=_row()).server,
        PlexClient(media_server=_row(url="http://other:32400")).server,
        PlexClient(media_server=_row(token="new-token")).server,
    }

    assert len(built) == 3
    assert len(servers) == 3


def test_reused_server_drops_cached_library_data(monkeypatch):
    _count_constructions(monkeypatch, "PlexServer", FakePlexServer)
    server = PlexClient(media_server=_row()).server
    server.__dict__["library"] = "sections from the last request"

    assert PlexClient(media_server=_row()).server is server
    assert "library" not in server.__dict__


def test_connection_cache_is_bounded(monkeypatch):
    _count_constructions(monkeypatch, "PlexServer", FakePlexServer)
    limit = plex_module._plex_servers.maxsize

    for i in range(limit + 10):
        assert PlexClient(media_server=_row(url=f"http://plex-{i}:32400")).server

    assert len(plex_module._plex_servers) <= limit


def test_failed_connection_is_tried_once_per_client_and_not_cached(monkeypatch):
    def offline(*args, **kwargs):
        raise requests.ConnectionError("offline")

    built = _count_constructions(monkeypatch, "PlexServer", offline)

    info = PlexClient(media_server=_row()).get_server_info()

    assert info == {
        "version": "Unknown",
        "transcoding_sessions": 0,
        "active_sessions": 0,
    }
    assert len(built) == 1  # before: one attempt for sessions, one for version

    PlexClient(media_server=_row()).get_server_info()
    assert len(built) == 2  # the failure was not cached


def test_transport_error_evicts_the_shared_server(monkeypatch):
    built = _count_constructions(monkeypatch, "PlexServer", FakePlexServer)
    server = PlexClient(media_server=_row()).server
    server.sessions = Mock(side_effect=requests.ConnectionError("reset"))

    with pytest.raises(requests.ConnectionError):
        PlexClient(media_server=_row()).now_playing()

    assert PlexClient(media_server=_row()).server is not server
    assert len(built) == 2


# ─── now_playing ────────────────────────────────────────────────────────────


def _playing_session(**overrides):
    values = {
        "viewOffset": 60_000,
        "duration": 120_000,
        "type": "movie",
        "title": "Heat",
        "players": [SimpleNamespace(state="playing", product="Plex Web", title="TV")],
        "usernames": ["sam"],
        "sessionKey": 12,
        "thumb": "/library/metadata/5/thumb/99",
        "image": None,
        "media": [],
        "transcodeSession": None,
        "transcodeSessions": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _client_with_server(server=None):
    client = PlexClient(media_server=_row())
    client._server = server or FakePlexServer("http://plex.local:32400", ADMIN_TOKEN)
    return client


def test_now_playing_raises_on_transport_error():
    client = _client_with_server()
    client._server.sessions = Mock(side_effect=requests.Timeout("slow"))

    with pytest.raises(requests.Timeout):
        client.now_playing()


def test_now_playing_returns_empty_list_only_for_no_sessions():
    assert _client_with_server().now_playing() == []


def test_now_playing_skips_one_broken_session():
    client = _client_with_server()
    broken = _playing_session(type=None)  # None.lower() raises AttributeError
    client._server.session_list = [broken, _playing_session()]

    sessions = client.now_playing()

    assert [s["media_title"] for s in sessions] == ["Heat"]


def test_now_playing_artwork_is_small_with_full_size_fallback():
    client = _client_with_server()
    client._server.session_list = [_playing_session()]

    (entry,) = client.now_playing()

    artwork = urlsplit(entry["artwork_url"])
    assert artwork.path == "/photo/:/transcode"
    query = parse_qs(artwork.query)
    assert query["url"] == ["/library/metadata/5/thumb/99"]
    assert query["width"] == ["240"]
    assert query["height"] == ["360"]
    assert entry["fallback_artwork_url"].startswith(
        "http://plex.local:32400/library/metadata/5/thumb/99?"
    )
    assert urlsplit(entry["thumbnail_url"]).path == "/photo/:/transcode"


# ─── User sync ──────────────────────────────────────────────────────────────


def _plex_user(user_id, email, *, all_libraries=False):
    share = SimpleNamespace(
        machineIdentifier=MACHINE_ID,
        allLibraries=all_libraries,
        # The old code called this once per user (an HTTP GET to plex.tv).
        sections=Mock(side_effect=AssertionError("per-user plex.tv call")),
    )
    return SimpleNamespace(
        id=user_id,
        email=email,
        title=email.split("@")[0],
        username=email.split("@")[0],
        thumb=None,
        home=False,
        admin=False,
        allowSync=False,
        allowChannels=False,
        allowCameraUpload=False,
        servers=[share],
    )


class _JsonResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _share(user_id, email, titles):
    return {
        "id": 1000 + user_id,
        "machineIdentifier": MACHINE_ID,
        "invitedId": user_id,
        "invited": {"email": email},
        "libraries": [{"id": i, "title": t} for i, t in enumerate(titles)],
    }


def _no_pending_writes():
    return not (db.session.new or db.session.deleted or db.session.dirty)


@pytest.fixture
def plex_row(session):
    row = MediaServer(
        name="Plex", server_type="plex", url="http://plex.local:32400", api_key="k"
    )
    session.add(row)
    session.commit()
    return row


def _add_user(row, email, libraries=None):
    user = User(email=email, username=email, token="t", code="c", server_id=row.id)
    if libraries is not None:
        user.set_accessible_libraries(libraries)
    db.session.add(user)
    db.session.commit()
    return user


def _sync_client(row, plex_users, shares_get):
    client = PlexClient(media_server=row)
    client._server = FakePlexServer(row.url, row.api_key)

    def users():
        assert _no_pending_writes(), "remote call while a DB write is pending"
        return plex_users

    def get(*args, **kwargs):
        assert _no_pending_writes(), "remote call while a DB write is pending"
        return shares_get(*args, **kwargs)

    admin = Mock(uuid="uuid", authToken=row.api_key)
    admin.users.side_effect = users
    admin._session.get.side_effect = get
    client._admin = admin
    return client, admin


def _libraries(email):
    return User.query.filter_by(email=email).one().get_accessible_libraries()


def test_sync_gets_all_library_shares_with_one_call(plex_row):
    _add_user(plex_row, "old@example.com", ["Movies"])
    plex_users = [
        _plex_user(1, "old@example.com"),
        _plex_user(2, "new@example.com"),
        _plex_user(3, "all@example.com", all_libraries=True),
    ]
    shares = [
        _share(1, "old@example.com", ["Movies", "Shows"]),
        _share(2, "new@example.com", ["Kids"]),
        {**_share(9, "x@example.com", ["Other"]), "machineIdentifier": "elsewhere"},
    ]
    client, admin = _sync_client(
        plex_row, plex_users, lambda *a, **k: _JsonResponse(shares)
    )

    client.list_users()

    assert admin._session.get.call_count == 1
    assert _libraries("old@example.com") == ["Movies", "Shows"]
    assert _libraries("new@example.com") == ["Kids"]
    assert _libraries("all@example.com") == []  # None means all libraries


def test_sync_keeps_library_access_when_the_bulk_call_fails(plex_row):
    _add_user(plex_row, "old@example.com", ["Movies"])
    plex_users = [_plex_user(1, "old@example.com"), _plex_user(2, "b@example.com")]

    def fail(*args, **kwargs):
        raise requests.ConnectionError("plex.tv down")

    client, admin = _sync_client(plex_row, plex_users, fail)

    client.list_users()

    assert admin._session.get.call_count == 1  # no fall back to one call per user
    assert _libraries("old@example.com") == ["Movies"]
    assert {u.email for u in User.query.filter_by(server_id=plex_row.id)} == {
        "old@example.com",
        "b@example.com",
    }


def test_sync_does_not_query_the_database_per_remote_user(app, plex_row):
    plex_users = [_plex_user(i, f"u{i}@example.com") for i in range(1, 6)]
    for plex_user in plex_users[:3]:
        _add_user(plex_row, plex_user.email)
    client, _admin = _sync_client(
        plex_row, plex_users, lambda *a, **k: _JsonResponse([])
    )

    statements = []

    def capture(_conn, _cursor, statement, *_args):
        statements.append(statement)

    event.listen(db.engine, "before_cursor_execute", capture)
    try:
        client.list_users()
    finally:
        event.remove(db.engine, "before_cursor_execute", capture)

    per_user_lookup = re.compile(r'"?user"?\.email = \?')
    assert not [s for s in statements if per_user_lookup.search(s)]
    assert User.query.filter_by(server_id=plex_row.id).count() == 5


def test_list_users_does_not_keep_the_client_alive(plex_row):
    # The old @cached key was the client object, so it never hit and kept
    # up to 1024 clients (and their sockets) alive.
    client, _admin = _sync_client(plex_row, [], lambda *a, **k: _JsonResponse([]))
    client.list_users()
    client_ref = weakref.ref(client)

    del client
    gc.collect()

    assert client_ref() is None


# ─── Delete ─────────────────────────────────────────────────────────────────


def _delete_client(plex_users):
    client = PlexClient(media_server=_row())
    admin = Mock()
    admin.users.return_value = list(plex_users)
    client._admin = admin
    return client, admin


def _account(user_id, email, *, home=False):
    return SimpleNamespace(
        id=user_id, email=email, username=email.split("@")[0], title="", home=home
    )


def test_batch_delete_downloads_the_user_list_once():
    friend_a = _account(1, "a@example.com")
    friend_b = _account(2, "b@example.com")
    home = _account(3, "h@example.com", home=True)
    client, admin = _delete_client([friend_a, friend_b, home])

    for email in ("a@example.com", "b@example.com", "h@example.com"):
        client.delete_user(email)

    assert admin.users.call_count == 1
    # plexapi skips its own user lookup when it gets a user object.
    assert [c.args[0] for c in admin.removeFriend.call_args_list] == [
        friend_a,
        friend_b,
    ]
    admin.removeHomeUser.assert_called_once_with(home)
    assert plex_module._get_cached_plex_users(ADMIN_TOKEN) == []


def test_delete_downloads_the_list_again_for_a_user_newer_than_the_cache():
    newcomer = _account(5, "new@example.com")
    client, admin = _delete_client([newcomer])
    plex_module._store_plex_users(ADMIN_TOKEN, [])  # cached before the invite

    client.delete_user("new@example.com")

    assert admin.users.call_count == 1
    admin.removeFriend.assert_called_once_with(newcomer)


def test_delete_of_user_removed_meanwhile_logs_and_returns():
    friend = _account(1, "a@example.com")
    client, admin = _delete_client([friend])
    admin.removeFriend.side_effect = NotFound("gone")

    client.delete_user("a@example.com")  # does not raise

    admin.removeFriend.assert_called_once_with(friend)


def test_invite_clears_the_cached_user_list():
    client, admin = _delete_client([])
    client._server = FakePlexServer("http://plex.local:32400", ADMIN_TOKEN)
    plex_module._store_plex_users(ADMIN_TOKEN, [_account(1, "a@example.com")])

    client.invite_friend("b@example.com", ["Movies"], False, False)

    assert plex_module._get_cached_plex_users(ADMIN_TOKEN) is None
    admin.inviteFriend.assert_called_once()


# ─── Posters ────────────────────────────────────────────────────────────────


class _FakeMovieSection:
    type = "movie"

    def recentlyAdded(self, maxresults):
        return [
            SimpleNamespace(thumb=f"/library/metadata/{i}/thumb/1700000000")
            for i in range(1, maxresults + 1)
        ]


class _ImageResponse:
    status_code = 200
    headers: ClassVar = {"Content-Type": "image/jpeg"}
    content = b"\xff\xd8\xff\xe0-small-jpeg"

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_posters_use_the_photo_transcoder_and_the_proxy_can_fetch_them(
    app, client, plex_row, monkeypatch
):
    plex_client = PlexClient(media_server=plex_row)
    fake_server = FakePlexServer(plex_row.url, plex_row.api_key)
    fake_server.library = SimpleNamespace(sections=lambda: [_FakeMovieSection()])
    plex_client._server = fake_server

    with app.app_context():
        posters = plex_client.get_movie_posters(limit=3)
        assert len(posters) == 3
        token = unquote_plus(posters[0].split("token=", 1)[1])
        upstream = ImageProxyService.validate_token(token)["url"]

    parts = urlsplit(upstream)
    assert f"{parts.scheme}://{parts.netloc}" == plex_row.url
    assert parts.path == "/photo/:/transcode"
    query = parse_qs(parts.query)
    assert query["url"] == ["/library/metadata/1/thumb/1700000000"]
    assert query["width"] == ["240"]
    assert query["height"] == ["360"]
    # The proxy removed the token from the URL; it sends it as a header.
    assert plex_row.api_key not in json.dumps(query)
    assert "X-Plex-Token" not in query

    captured = {}

    class _FakeSession:
        def get(self, url, headers=None, timeout=None, **kwargs):
            captured["url"] = url
            captured["headers"] = headers or {}
            return _ImageResponse()

    monkeypatch.setattr(
        ImageProxyService,
        "get_session",
        classmethod(lambda cls, url, server_id: _FakeSession()),
    )

    resp = client.get(posters[0])

    assert resp.status_code == 200
    assert urlsplit(captured["url"]).path == "/photo/:/transcode"
    assert captured["headers"].get("X-Plex-Token") == plex_row.api_key


def test_posters_fall_back_to_original_when_transcoder_is_off():
    plex_client = _client_with_server()
    plex_client._server.transcoderPhoto = False

    url = plex_client._small_image_url("/library/metadata/1/thumb/2")

    assert (
        url
        == f"http://plex.local:32400/library/metadata/1/thumb/2?X-Plex-Token={ADMIN_TOKEN}"
    )
