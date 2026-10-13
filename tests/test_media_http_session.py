"""The REST media clients share one pooled HTTP session with tuple timeouts.

Before, ``RestApiMixin._request`` called ``requests.request`` with
``timeout=60``. Each call opened a new TCP/TLS connection, and an offline host
held the caller for the full minute.
"""

import threading

import pytest
import requests

from app.services.media import client_base
from app.services.media.client_base import (
    DEFAULT_TIMEOUT,
    RestApiMixin,
    get_http_session,
)
from app.services.media.jellyfin import JellyfinClient


class _Response:
    status_code = 200

    def raise_for_status(self):
        return None


class _RecordingSession:
    def __init__(self):
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return _Response()


@pytest.fixture
def recording_session(monkeypatch):
    session = _RecordingSession()
    monkeypatch.setattr(client_base, "get_http_session", lambda: session)
    return session


def _client():
    client = JellyfinClient.__new__(JellyfinClient)
    client.url = "http://jellyfin.local/"
    client.token = "token"
    return client


def test_request_uses_shared_session_and_default_tuple_timeout(recording_session):
    _client().get("/System/Info")

    method, url, kwargs = recording_session.calls[0]
    assert (method, url) == ("GET", "http://jellyfin.local/System/Info")
    assert kwargs["timeout"] == DEFAULT_TIMEOUT
    # A short connect timeout makes an offline host fail fast.
    assert isinstance(DEFAULT_TIMEOUT, tuple)
    assert DEFAULT_TIMEOUT[0] <= 5


def test_timeout_can_be_set_per_client(recording_session):
    client = _client()
    client.timeout = (3, 10)

    client.get("/Sessions")

    assert recording_session.calls[0][2]["timeout"] == (3, 10)


def test_timeout_can_be_set_per_call(recording_session):
    client = _client()
    client.timeout = (3, 10)

    client.get("/Users", timeout=(1, 2))

    assert recording_session.calls[0][2]["timeout"] == (1, 2)


def test_every_media_client_has_a_timeout_attribute():
    # Clients made without __init__ (as in many tests) still get the default.
    for cls in client_base.CLIENTS.values():
        assert cls.__new__(cls).timeout == DEFAULT_TIMEOUT
    assert issubclass(JellyfinClient, RestApiMixin)


def test_shared_session_is_reused_across_threads():
    sessions = []

    def grab():
        sessions.append(get_http_session())

    threads = [threading.Thread(target=grab) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len({id(s) for s in sessions}) == 1
    assert sessions[0] is get_http_session()
    adapter = sessions[0].get_adapter("https://example.com")
    assert isinstance(adapter, requests.adapters.HTTPAdapter)


def test_shared_session_keeps_no_cookies():
    """Each call used a new Session before, so no cookie went to a later call."""
    session = get_http_session()
    request = requests.Request("GET", "http://media.local/login").prepare()
    headers = {"Set-Cookie": "sid=secret; Path=/"}

    # Control: the fake response gives the cookie to a plain Session.
    plain = requests.Session()
    requests.cookies.extract_cookies_to_jar(
        plain.cookies, request, _RawHeaders(headers)
    )
    assert len(plain.cookies) == 1

    requests.cookies.extract_cookies_to_jar(
        session.cookies, request, _RawHeaders(headers)
    )
    assert len(session.cookies) == 0


def test_new_session_after_fork(monkeypatch):
    first = get_http_session()
    monkeypatch.setattr(client_base.os, "getpid", lambda: -1)

    second = get_http_session()

    assert second is not first


class _RawHeaders:
    """Minimal urllib3-like response so extract_cookies_to_jar can read headers."""

    def __init__(self, headers):
        self._original_response = _OriginalResponse(headers)


class _OriginalResponse:
    def __init__(self, headers):
        self.msg = _Message(headers)


class _Message:
    def __init__(self, headers):
        self._headers = headers

    def get_all(self, name, default=None):
        value = self._headers.get(name)
        return [value] if value is not None else default
