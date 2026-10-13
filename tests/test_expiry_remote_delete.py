"""
Expiry must not forget a user the media server failed to remove.

The remote delete used to be swallowed, so the local row was deleted and the
user kept their access on the server, untracked. Now a failure keeps the row
for the next run, and a user the server no longer has still counts as gone.
"""

from unittest.mock import Mock

import pytest
import requests
from plexapi.exceptions import BadRequest, NotFound

from app.extensions import db
from app.models import ExpiredUser, User
from app.services import expiry
from app.services.media import service
from app.services.media.plex import PlexClient
from tests.expiry_helpers import add_expired_users


def _http_error(status: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(response=response)


@pytest.fixture
def expired_user(session, monkeypatch):
    monkeypatch.setattr(expiry.time, "sleep", lambda _seconds: None)
    [user_id] = add_expired_users(session)
    return user_id


def _remote_delete_raises(monkeypatch, exc):
    client = Mock()
    client.delete_user.side_effect = exc
    monkeypatch.setattr(service, "get_client_for_media_server", lambda _s: client)
    return client


def test_user_already_gone_on_the_server_is_expired(expired_user, monkeypatch):
    _remote_delete_raises(monkeypatch, _http_error(404))

    assert expiry.disable_or_delete_user_if_expired() == [expired_user]
    assert db.session.get(User, expired_user) is None
    assert ExpiredUser.query.count() == 1


def test_admin_delete_still_removes_the_local_row(expired_user, monkeypatch):
    _remote_delete_raises(monkeypatch, requests.ConnectionError("server down"))

    service.delete_user(expired_user)
    assert db.session.get(User, expired_user) is None


def _plex_client(remove_home, remove_friend, users=()):
    client = PlexClient.__new__(PlexClient)
    admin = Mock()
    admin.users.return_value = list(users)
    admin.removeHomeUser.side_effect = remove_home
    admin.removeFriend.side_effect = remove_friend
    client._admin = admin
    return client, admin


def _plex_friend():
    return Mock(title="sam", username="sam", email="sam@example.com", id=7, home=False)


def test_plex_delete_raises_when_plex_fails():
    client, _admin = _plex_client(
        BadRequest("not home"), requests.ConnectionError("down"), [_plex_friend()]
    )
    with pytest.raises(requests.ConnectionError):
        client.delete_user("sam@example.com")


def test_plex_delete_of_unknown_user_counts_as_removed():
    # delete_user looks the user up first; a user Plex does not list is gone.
    client, admin = _plex_client(NotFound("no user"), NotFound("no user"))
    client.delete_user("sam@example.com")
    admin.removeFriend.assert_not_called()


def test_plex_delete_of_user_removed_meanwhile_counts_as_removed():
    friend = _plex_friend()
    client, admin = _plex_client(NotFound("no user"), NotFound("no user"), [friend])
    client.delete_user("sam@example.com")
    admin.removeFriend.assert_called_once_with(friend)
