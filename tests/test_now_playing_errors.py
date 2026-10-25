"""now_playing() raises when the session list cannot be fetched.

The activity monitor ends all active sessions when now_playing() returns [].
So [] must mean only that the server reported no sessions. A failed fetch
(HTTP error, connection error, timeout or invalid JSON) must raise, so that
the monitor skips the cycle. One malformed session is skipped, and the other
sessions are still returned.

All HTTP calls go to a fake session. No test uses the network.
"""

import time

import pytest
import requests

from app.services.media import client_base
from app.services.media.audiobookshelf import AudiobookshelfClient
from app.services.media.drop import DropClient
from app.services.media.emby import EmbyClient
from app.services.media.jellyfin import JellyfinClient
from app.services.media.kavita import KavitaClient
from app.services.media.komga import KomgaClient
from app.services.media.navidrome import NavidromeClient


class _Response:
    def __init__(self, payload=None, status_code=200, invalid_json=False):
        self._payload = payload
        self.status_code = status_code
        self._invalid_json = invalid_json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)

    def json(self):
        if self._invalid_json:
            raise requests.JSONDecodeError("Expecting value", "<html>", 0)
        return self._payload


class _FakeSession:
    """Return the queued results in order. An exception result is raised."""

    def __init__(self, results):
        self.results = list(results)
        self.urls = []

    def request(self, method, url, **kwargs):
        self.urls.append(url)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def fake_http(monkeypatch):
    def install(*results):
        session = _FakeSession(results)
        monkeypatch.setattr(client_base, "get_http_session", lambda: session)
        return session

    return install


ADMIN_TOKEN = "admin-key"  # test fixture, not a real credential


def _client(cls):
    client = cls.__new__(cls)
    client.url = "http://media.local"
    client.token = ADMIN_TOKEN
    client.server_id = None
    return client


TRANSPORT_FAILURES = [
    pytest.param(requests.ConnectionError("refused"), id="connection"),
    pytest.param(requests.Timeout("slow"), id="timeout"),
    pytest.param(_Response(status_code=500), id="http-500"),
    pytest.param(_Response(invalid_json=True), id="invalid-json"),
]


# ─── Jellyfin and Emby ──────────────────────────────────────────────────────


def _jellyfin_session(session_id, name="Heat", **overrides):
    session = {
        "Id": session_id,
        "UserName": "sam",
        "UserId": "u1",
        "NowPlayingItem": {
            "Id": f"item-{session_id}",
            "Name": name,
            "Type": "Movie",
            "RunTimeTicks": 100,
        },
        "PlayState": {"PositionTicks": 50, "IsPaused": False},
    }
    session.update(overrides)
    return session


@pytest.mark.parametrize("cls", [JellyfinClient, EmbyClient])
@pytest.mark.parametrize("failure", TRANSPORT_FAILURES)
def test_jellyfin_family_raises_when_the_session_list_fails(cls, failure, fake_http):
    fake_http(failure)

    with pytest.raises(Exception):  # noqa: B017 - any failure must raise
        _client(cls).now_playing()


@pytest.mark.parametrize("cls", [JellyfinClient, EmbyClient])
def test_jellyfin_family_raises_when_the_list_is_not_a_list(cls, fake_http):
    fake_http(_Response({"error": "unexpected"}))

    with pytest.raises(ValueError, match="invalid session list"):
        _client(cls).now_playing()


@pytest.mark.parametrize("cls", [JellyfinClient, EmbyClient])
def test_jellyfin_family_returns_empty_list_only_for_no_sessions(cls, fake_http):
    idle = {"Id": "idle", "UserName": "sam"}  # connected, nothing plays
    fake_http(_Response([idle]))

    assert _client(cls).now_playing() == []


@pytest.mark.parametrize("cls", [JellyfinClient, EmbyClient])
def test_jellyfin_family_skips_one_broken_session(cls, fake_http, caplog):
    broken = _jellyfin_session("bad", PlayState="not-a-dict")
    fake_http(_Response([broken, _jellyfin_session("good")]))

    sessions = _client(cls).now_playing()

    assert [s["session_id"] for s in sessions] == ["good"]
    assert "Failed to read a" in caplog.text


def test_jellyfin_session_shape_is_unchanged(fake_http):
    fake_http(_Response([_jellyfin_session("s1")]))

    (entry,) = _client(JellyfinClient).now_playing()

    assert entry["user_name"] == "sam"
    assert entry["media_title"] == "Heat"
    assert entry["state"] == "playing"
    assert entry["progress"] == 0.5
    assert entry["metadata"]["jellyfin_item_id"] == "item-s1"
    assert set(entry["transcoding_info"]) == {
        "is_transcoding",
        "video_codec",
        "audio_codec",
        "container",
        "video_resolution",
        "transcoding_speed",
        "direct_play",
    }


# ─── Audiobookshelf ─────────────────────────────────────────────────────────


def _abs_session(session_id, **overrides):
    session = {
        "id": session_id,
        "userId": "u1",
        "displayTitle": "Dune",
        "updatedAt": int(time.time() * 1000),
        "currentTime": 30,
        "duration": 60,
    }
    session.update(overrides)
    return session


@pytest.mark.parametrize("failure", TRANSPORT_FAILURES)
def test_abs_raises_when_the_metadata_request_fails(failure, fake_http):
    fake_http(failure)

    with pytest.raises(Exception):  # noqa: B017 - any failure must raise
        _client(AudiobookshelfClient).now_playing()


@pytest.mark.parametrize("failure", TRANSPORT_FAILURES)
def test_abs_raises_when_the_session_page_fails(failure, fake_http):
    fake_http(_Response({"total": 3}), failure)

    with pytest.raises(Exception):  # noqa: B017 - any failure must raise
        _client(AudiobookshelfClient).now_playing()


def test_abs_raises_when_the_session_page_has_no_list(fake_http):
    fake_http(_Response({"total": 3}), _Response({"sessions": "oops"}))

    with pytest.raises(ValueError, match="invalid session list"):
        _client(AudiobookshelfClient).now_playing()


def test_abs_returns_empty_list_for_no_sessions(fake_http):
    fake_http(_Response({"total": 0}))

    assert _client(AudiobookshelfClient).now_playing() == []


def test_abs_skips_one_broken_session(fake_http, caplog):
    broken = _abs_session("bad", currentTime="not-a-number")
    stale = _abs_session("stale", updatedAt=0)
    fake_http(
        _Response({"total": 3}),
        _Response({"sessions": [broken, "not-a-dict", stale, _abs_session("good")]}),
    )

    sessions = _client(AudiobookshelfClient).now_playing()

    assert [s["session_id"] for s in sessions] == ["good"]
    assert sessions[0]["progress"] == 0.5
    assert "failed to read a session" in caplog.text


def test_abs_statistics_still_works_when_sessions_fail(fake_http):
    fake_http(
        requests.ConnectionError("refused"),  # now_playing
        _Response([{"id": "u1"}, {"id": "u2"}]),  # /users
    )

    stats = _client(AudiobookshelfClient).statistics()

    assert stats["user_stats"]["active_sessions"] == 0
    assert stats["user_stats"]["total_users"] == 2


# ─── Navidrome ──────────────────────────────────────────────────────────────


def _subsonic(now_playing):
    return _Response({"subsonic-response": {"status": "ok", "nowPlaying": now_playing}})


@pytest.mark.parametrize("failure", TRANSPORT_FAILURES)
def test_navidrome_raises_when_the_request_fails(failure, fake_http):
    fake_http(failure)

    with pytest.raises(Exception):  # noqa: B017 - any failure must raise
        _client(NavidromeClient).now_playing()


def test_navidrome_raises_on_a_subsonic_error(fake_http):
    fake_http(
        _Response(
            {"subsonic-response": {"status": "failed", "error": {"message": "auth"}}}
        )
    )

    with pytest.raises(Exception, match="Subsonic API error"):
        _client(NavidromeClient).now_playing()


def test_navidrome_raises_when_the_entries_are_invalid(fake_http):
    fake_http(_subsonic({"entry": "oops"}))

    with pytest.raises(ValueError, match="invalid now playing list"):
        _client(NavidromeClient).now_playing()


def test_navidrome_returns_empty_list_for_no_sessions(fake_http):
    fake_http(_subsonic({}))

    assert _client(NavidromeClient).now_playing() == []


def test_navidrome_skips_one_broken_entry(fake_http, caplog):
    good = {"id": "t1", "username": "sam", "title": "Song", "duration": 3}
    fake_http(_subsonic({"entry": ["not-a-dict", good]}))

    sessions = _client(NavidromeClient).now_playing()

    assert [s["session_id"] for s in sessions] == ["t1"]
    assert sessions[0]["duration_ms"] == 3000
    assert "failed to read a session" in caplog.text


def test_navidrome_single_entry_is_a_list(fake_http):
    fake_http(_subsonic({"entry": {"id": "t1", "username": "sam"}}))

    assert [s["session_id"] for s in _client(NavidromeClient).now_playing()] == ["t1"]


def test_navidrome_statistics_still_works_when_sessions_fail(fake_http):
    fake_http(
        _Response(
            {
                "subsonic-response": {
                    "status": "ok",
                    "users": {"user": [{"username": "a"}, {"username": "b"}]},
                }
            }
        ),
        requests.ConnectionError("refused"),  # now_playing
    )

    stats = _client(NavidromeClient).statistics()

    assert stats["user_stats"] == {"total_users": 2, "active_sessions": 0}


# ─── Servers without a session API ──────────────────────────────────────────


# RomM gained a session API (GET /api/activity), so it is deliberately not in
# this list – its now_playing() does make a request.
@pytest.mark.parametrize("cls", [KavitaClient, KomgaClient, DropClient])
def test_servers_without_sessions_make_no_request(cls, fake_http):
    session = fake_http()

    assert _client(cls).now_playing() == []
    assert session.urls == []
