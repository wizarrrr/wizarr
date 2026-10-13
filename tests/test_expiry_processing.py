import datetime
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import ExpiredUser, Settings, User
from app.services import expiry
from app.services.media import service as media_service
from tests.expiry_helpers import add_expired_users


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(expiry.time, "sleep", lambda _seconds: None)


def test_disable_expired_user_is_idempotent(session, monkeypatch):
    [user_id] = add_expired_users(session, action="disable")
    disable_user = Mock(return_value=True)
    monkeypatch.setattr(expiry, "disable_user", disable_user)

    assert expiry.disable_or_delete_user_if_expired() == [user_id]
    assert expiry.disable_or_delete_user_if_expired() == []

    assert ExpiredUser.query.count() == 1
    assert db.session.get(User, user_id).is_disabled is True
    disable_user.assert_called_once_with(user_id, commit=False)


def test_expired_user_without_server_is_deleted(session):
    [user_id] = add_expired_users(session, server_type=None)

    assert expiry.disable_or_delete_user_if_expired() == [user_id]

    assert db.session.get(User, user_id) is None
    assert ExpiredUser.query.count() == 1


@pytest.mark.parametrize(
    "failure",
    [{"return_value": False}, {"side_effect": RuntimeError("server down")}],
    ids=["returns-false", "raises"],
)
def test_failed_disable_keeps_the_user_for_retry(session, monkeypatch, failure):
    """A failed disable must not fall back to a delete.

    The admin chose to keep the account, and the server can be down for a
    short time only. The user stays enabled, with no expiry history, and the
    next run disables it.
    """
    [user_id] = add_expired_users(session, action="disable")
    monkeypatch.setattr(expiry, "disable_user", Mock(**failure))
    delete = Mock()
    monkeypatch.setattr(expiry, "delete_user", delete)

    assert expiry.disable_or_delete_user_if_expired() == []

    delete.assert_not_called()
    user = db.session.get(User, user_id)
    assert user is not None
    assert user.is_disabled is False
    assert ExpiredUser.query.count() == 0

    monkeypatch.setattr(expiry, "disable_user", Mock(return_value=True))
    assert expiry.disable_or_delete_user_if_expired() == [user_id]
    assert db.session.get(User, user_id).is_disabled is True


@pytest.mark.parametrize("action", ["disable", "delete", "legacy_delete"])
def test_reenabled_expired_user_reuses_history(session, monkeypatch, action):
    [user_id] = add_expired_users(session, action="disable")
    user = db.session.get(User, user_id)
    setting = Settings.query.filter_by(key="expiry_action").one()
    original_expiry = user.expires
    media_client = Mock()
    media_client.disable_user.return_value = True
    media_client.enable_user.return_value = True
    monkeypatch.setattr(
        media_service, "get_client_for_media_server", lambda _server: media_client
    )

    assert expiry.disable_or_delete_user_if_expired() == [user_id]
    history = ExpiredUser.query.one()
    history_id, recorded_at = history.id, history.deleted_at
    # Exercise the same service called by the API enable endpoint.
    assert media_service.enable_user(user_id) is True
    assert user.is_disabled is False
    assert user.expires == original_expiry
    setting.value = "delete" if action == "delete" else "disable"
    session.commit()

    process = (
        expiry.delete_user_if_expired
        if action == "legacy_delete"
        else expiry.disable_or_delete_user_if_expired
    )
    assert process() == [user_id]
    assert process() == []
    history = ExpiredUser.query.one()
    assert (history.id, history.deleted_at) == (history_id, recorded_at)
    if action == "disable":
        refreshed = db.session.get(User, user_id)
        assert refreshed is not None
        assert refreshed.is_disabled is True
        assert media_client.disable_user.call_count == 2
        media_client.delete_user.assert_not_called()
    else:
        assert db.session.get(User, user_id) is None
        media_client.delete_user.assert_called_once()


def test_concurrent_new_history_claim_failure_prevents_media_action(
    session, monkeypatch
):
    [user_id] = add_expired_users(session, server_type=None)
    delete_user = Mock()
    monkeypatch.setattr(expiry, "delete_user", delete_user)
    original_flush = db.session.flush

    def reject_new_event(*args, **kwargs):
        if any(isinstance(row, ExpiredUser) for row in db.session.new):
            raise IntegrityError(
                "synthetic concurrent claim", {}, Exception("duplicate")
            )
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db.session, "flush", reject_new_event)
    assert expiry.disable_or_delete_user_if_expired() == []
    delete_user.assert_not_called()
    assert ExpiredUser.query.count() == 0
    assert db.session.get(User, user_id) is not None


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (3, [(3, "urgent")]),
        (5, [(5, "soon")]),
        (-1, []),  # Already expired.
        (10, []),  # Not in the next 7 days.
    ],
)
def test_expiring_this_week_users(session, days, expected):
    """SQLite gives back naive datetimes.

    The service must not compare them with aware datetimes (TypeError).
    """
    session.add(
        User(
            token="t",
            username="expiring",
            email="expiring@example.com",
            code="C",
            expires=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days),
        )
    )
    session.commit()

    result = expiry.get_expiring_this_week_users()

    assert [(r["days_left"], r["urgency"]) for r in result] == expected
    assert all(r["user"].username == "expiring" for r in result)
