"""
Expiry must keep a user whose disable failed, and try again on the next run.

With the expiry action set to "disable", a failed disable used to fall back to
deleting the user. On a server where the disable half-worked or the server was
only briefly down, that removed the account (and its history) the admin meant
to keep. Now the row stays, enabled, with no expiry history, for the next run.
"""

import datetime
from unittest.mock import Mock

import pytest

from app.extensions import db
from app.models import ExpiredUser, MediaServer, Settings, User
from app.services import expiry


@pytest.fixture
def expired_user(app, session, monkeypatch):
    monkeypatch.setattr(expiry.time, "sleep", lambda _seconds: None)
    server = MediaServer(
        name="ABS", server_type="audiobookshelf", url="http://abs.local", api_key="k"
    )
    session.add_all([server, Settings(key="expiry_action", value="disable")])
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


@pytest.mark.parametrize(
    "failure",
    [{"return_value": False}, {"side_effect": RuntimeError("server down")}],
    ids=["returns-false", "raises"],
)
def test_failed_disable_keeps_the_user_for_retry(expired_user, monkeypatch, failure):
    monkeypatch.setattr(expiry, "disable_user", Mock(**failure))
    delete = Mock()
    monkeypatch.setattr(expiry, "delete_user", delete)

    assert expiry.disable_or_delete_user_if_expired() == []

    delete.assert_not_called()
    user = db.session.get(User, expired_user)
    assert user is not None
    assert user.is_disabled is False
    assert ExpiredUser.query.count() == 0


def test_the_next_run_disables_it_once_the_server_answers(expired_user, monkeypatch):
    monkeypatch.setattr(expiry, "disable_user", Mock(return_value=False))
    assert expiry.disable_or_delete_user_if_expired() == []

    monkeypatch.setattr(expiry, "disable_user", Mock(return_value=True))
    assert expiry.disable_or_delete_user_if_expired() == [expired_user]
    user = db.session.get(User, expired_user)
    assert user is not None
    assert user.is_disabled is True
