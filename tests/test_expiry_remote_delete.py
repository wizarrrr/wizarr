"""
Expiry must not forget a user the media server failed to remove.

The remote delete used to be swallowed, so the local row was deleted and the
user kept their access on the server, untracked. Now a failure keeps the row
for the next run, and a user the server no longer has still counts as gone.
"""

import datetime
from unittest.mock import Mock

import pytest
import requests
from plexapi.exceptions import BadRequest, NotFound

from app.extensions import db
from app.models import ExpiredUser, MediaServer, User
from app.services import expiry
from app.services.media import service
from app.services.media.plex import PlexClient


def _http_error(status: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(response=response)


@pytest.fixture
def expired_user(app, session, monkeypatch):
    monkeypatch.setattr(expiry.time, "sleep", lambda _seconds: None)
    server = MediaServer(
        name="J", server_type="jellyfin", url="http://j.local", api_key="k"
    )
    session.add(server)
    session.flush()
    user = User(
        token="remote-id",
        username="sam",
        email="sam@example.com",
        code="EXPIRED",
        expires=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1),
        server_id=server.id,
    )
    session.add(user)
    session.commit()
    return user.id


def _remote_delete_raises(monkeypatch, exc):
    client = Mock()
    client.delete_user.side_effect = exc
    monkeypatch.setattr(service, "get_client_for_media_server", lambda _s: client)
    return client


def test_failed_remote_delete_keeps_the_user_for_retry(expired_user, monkeypatch):
    _remote_delete_raises(monkeypatch, requests.ConnectionError("server down"))

    assert expiry.disable_or_delete_user_if_expired() == []
    assert db.session.get(User, expired_user) is not None
    assert ExpiredUser.query.count() == 0


def test_user_already_gone_on_the_server_is_expired(expired_user, monkeypatch):
    _remote_delete_raises(monkeypatch, _http_error(404))

    assert expiry.disable_or_delete_user_if_expired() == [expired_user]
    assert db.session.get(User, expired_user) is None
    assert ExpiredUser.query.count() == 1


def test_admin_delete_still_removes_the_local_row(expired_user, monkeypatch):
    _remote_delete_raises(monkeypatch, requests.ConnectionError("server down"))

    service.delete_user(expired_user)
    assert db.session.get(User, expired_user) is None


def _plex_client(remove_home, remove_friend):
    client = PlexClient.__new__(PlexClient)
    admin = Mock()
    admin.removeHomeUser.side_effect = remove_home
    admin.removeFriend.side_effect = remove_friend
    client._admin = admin
    return client, admin


def test_plex_delete_raises_when_plex_fails():
    client, _admin = _plex_client(
        BadRequest("not home"), requests.ConnectionError("down")
    )
    with pytest.raises(requests.ConnectionError):
        client.delete_user("sam@example.com")


def test_plex_delete_of_unknown_user_counts_as_removed():
    client, admin = _plex_client(NotFound("no user"), NotFound("no user"))
    client.delete_user("sam@example.com")
    admin.removeFriend.assert_called_once_with("sam@example.com")
