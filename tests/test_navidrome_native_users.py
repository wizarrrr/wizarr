"""Navidrome user management must use the native REST API.

Navidrome's Subsonic ``createUser``/``updateUser``/``deleteUser`` endpoints
answer 501 Not Implemented, and Subsonic ``getUsers`` only returns the
logged-in user. The client therefore logs in via ``POST /auth/login`` and
manages users through ``/api/user`` with the ``x-nd-authorization`` bearer
header. No test uses the network.
"""

from unittest.mock import patch

import pytest
import requests

from app.services.media import client_base
from app.services.media.navidrome import NavidromeClient

ADMIN_TOKEN = "admin-key"  # test fixture, not a real credential


class _Response:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)

    def json(self):
        if self._payload is None:
            raise requests.JSONDecodeError("Expecting value", "", 0)
        return self._payload


class _FakeSession:
    """Serve queued responses and record every request."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        result.raise_for_status()
        return result


@pytest.fixture
def fake_http(monkeypatch):
    def install(*results):
        session = _FakeSession(results)
        monkeypatch.setattr(client_base, "get_http_session", lambda: session)
        return session

    return install


def _client():
    client = NavidromeClient.__new__(NavidromeClient)
    client.url = "http://music.local"
    client.token = ADMIN_TOKEN
    client.server_id = None
    client._native_token = None
    return client


LOGIN_OK = _Response({"token": "jwt-1", "id": "admin-id", "isAdmin": True})

SAM = {
    "id": "nd-1",
    "userName": "sam",
    "name": "sam",
    "email": "sam@example.com",
    "isAdmin": False,
    "createdAt": "2026-01-02T03:04:05.123456789Z",
    "lastAccessAt": "2026-02-03T04:05:06Z",
}


# ─── login ───────────────────────────────────────────────────────────────────


def test_login_sends_admin_credentials_and_caches_the_token(fake_http):
    http = fake_http(LOGIN_OK, _Response([]))

    _client()._native_users()

    method, url, kwargs = http.calls[0]
    assert (method, url) == ("POST", "http://music.local/auth/login")
    assert kwargs["json"] == {"username": "admin", "password": ADMIN_TOKEN}
    assert http.calls[1][2]["headers"]["x-nd-authorization"] == "Bearer jwt-1"


def test_login_failure_raises(fake_http):
    fake_http(_Response({"error": "Invalid username or password"}, 401))

    with pytest.raises(requests.HTTPError):
        _client().create_user("sam", "Password1", "sam@example.com")


def test_login_without_a_token_in_the_response_raises(fake_http):
    fake_http(_Response({"id": "admin-id"}))

    with pytest.raises(ValueError, match="did not return a token"):
        _client()._native_users()


def test_an_expired_token_is_renewed_exactly_once(fake_http):
    http = fake_http(
        _Response(None, 401),  # expired JWT
        LOGIN_OK,  # re-login
        _Response([SAM]),  # retried request
    )
    client = _client()
    client._native_token = "stale-jwt"

    assert client._native_users() == [SAM]
    assert http.calls[2][2]["headers"]["x-nd-authorization"] == "Bearer jwt-1"


def test_a_second_consecutive_401_raises(fake_http):
    fake_http(_Response(None, 401), LOGIN_OK, _Response(None, 401))
    client = _client()
    client._native_token = "stale-jwt"

    with pytest.raises(requests.HTTPError):
        client._native_users()


# ─── create ──────────────────────────────────────────────────────────────────


def test_create_user_posts_the_native_payload_and_returns_the_id(fake_http):
    http = fake_http(LOGIN_OK, _Response(SAM))

    user_id = _client().create_user("sam", "Password1", "sam@example.com")

    assert user_id == "nd-1"
    method, url, kwargs = http.calls[1]
    assert (method, url) == ("POST", "http://music.local/api/user")
    assert kwargs["json"] == {
        "userName": "sam",
        "name": "sam",
        "email": "sam@example.com",
        "password": "Password1",
        "isAdmin": False,
    }


def test_create_user_without_an_id_in_the_response_confirms_by_lookup(fake_http):
    fake_http(
        LOGIN_OK,
        _Response({}),  # create answered without an id
        _Response(None, 404),  # GET /api/user/sam
        _Response([SAM]),  # GET /api/user
    )

    assert _client().create_user("sam", "Password1", "sam@example.com") == "nd-1"


def test_create_user_reports_failure_instead_of_false_success(fake_http):
    fake_http(
        LOGIN_OK,
        _Response({}),  # create answered without an id
        _Response(None, 404),  # GET /api/user/sam
        _Response([]),  # user list does not contain sam
    )

    with pytest.raises(requests.HTTPError):
        _client().create_user("sam", "Password1", "sam@example.com")


def test_create_user_warns_that_download_restrictions_are_not_enforced(fake_http):
    fake_http(LOGIN_OK, _Response(SAM))

    with patch.object(NavidromeClient, "_warn_downloads_unenforceable") as warn:
        _client().create_user(
            "sam", "Password1", "sam@example.com", allow_downloads=False
        )

    warn.assert_called_once()


# ─── delete ──────────────────────────────────────────────────────────────────


def test_delete_user_by_native_id(fake_http):
    http = fake_http(LOGIN_OK, _Response(SAM), _Response({"id": "nd-1"}))

    _client().delete_user("nd-1")

    assert http.calls[2][:2] == ("DELETE", "http://music.local/api/user/nd-1")


def test_delete_user_with_a_legacy_username_token(fake_http):
    http = fake_http(
        LOGIN_OK,
        _Response(None, 404),  # GET /api/user/sam
        _Response([SAM]),  # username lookup
        _Response({"id": "nd-1"}),
    )

    _client().delete_user("sam")

    assert http.calls[3][:2] == ("DELETE", "http://music.local/api/user/nd-1")


def test_delete_user_surfaces_404_for_an_unknown_user(fake_http):
    fake_http(LOGIN_OK, _Response(None, 404), _Response([]))

    with pytest.raises(requests.HTTPError) as excinfo:
        _client().delete_user("ghost")

    assert excinfo.value.response.status_code == 404


# ─── update ──────────────────────────────────────────────────────────────────


def test_update_user_merges_the_record_and_puts_the_full_object(fake_http):
    http = fake_http(LOGIN_OK, _Response(SAM), _Response(SAM))

    _client().update_user("nd-1", {"email": "new@example.com", "is_admin": True})

    method, url, kwargs = http.calls[2]
    assert (method, url) == ("PUT", "http://music.local/api/user/nd-1")
    assert kwargs["json"] == {
        "id": "nd-1",
        "userName": "sam",
        "name": "sam",
        "email": "new@example.com",
        "isAdmin": True,
    }
    assert "password" not in kwargs["json"]


def test_update_user_includes_a_new_password_only_when_given(fake_http):
    http = fake_http(LOGIN_OK, _Response(SAM), _Response(SAM))

    _client().update_user("nd-1", {"password": "NewPass123"})

    assert http.calls[2][2]["json"]["password"] == "NewPass123"


# ─── details ─────────────────────────────────────────────────────────────────


def test_get_user_details_maps_the_native_record(fake_http):
    fake_http(LOGIN_OK, _Response(SAM))

    details = _client().get_user_details("nd-1")

    assert details.user_id == "nd-1"
    assert details.username == "sam"
    assert details.email == "sam@example.com"
    assert details.is_admin is False
    assert details.created_at is not None and details.created_at.year == 2026
    assert details.last_active is not None and details.last_active.month == 2


# ─── sync ────────────────────────────────────────────────────────────────────


def _server(session):
    from app.models import MediaServer

    server = MediaServer(
        name="music",
        server_type="navidrome",
        url="http://music.local",
        api_key=ADMIN_TOKEN,
    )
    session.add(server)
    session.commit()
    return server


def test_list_users_syncs_and_migrates_legacy_username_tokens(session):
    from app.models import User

    server = _server(session)
    session.add(
        User(
            token="sam",  # legacy rows stored the username
            username="sam",
            email="old@example.com",
            code="empty",
            server_id=server.id,
        )
    )
    session.commit()

    client = NavidromeClient.__new__(NavidromeClient)
    client.url = server.url
    client.token = ADMIN_TOKEN
    client.server_id = server.id

    admin = {"id": "nd-0", "userName": "admin", "email": "", "isAdmin": True}
    with patch.object(NavidromeClient, "_native_users", return_value=[admin, SAM]):
        users = client.list_users()

    by_name = {u.username: u for u in users}
    assert set(by_name) == {"admin", "sam"}
    assert by_name["sam"].token == "nd-1"  # migrated to the native id
    assert by_name["sam"].email == "sam@example.com"
    assert by_name["admin"].is_admin is True
    assert by_name["sam"].is_admin is False
