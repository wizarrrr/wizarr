import datetime
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import ExpiredUser, MediaServer, Settings, User
from app.services import expiry


def _expired_user(*, server_id: int | None = None) -> User:
    return User(
        token="expired-user-token",
        username="expired-user",
        email="expired@example.com",
        code="EXPIRED",
        expires=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1),
        server_id=server_id,
    )


def test_disable_expired_user_is_idempotent(app, session, monkeypatch):
    with app.app_context():
        server = MediaServer(
            name="Jellyfin",
            server_type="jellyfin",
            url="http://jellyfin.example.com",
            api_key="test-key",
        )
        session.add(server)
        session.flush()

        user = _expired_user(server_id=server.id)
        session.add_all([user, Settings(key="expiry_action", value="disable")])
        session.commit()
        user_id = user.id

        disable_user = Mock(return_value=True)
        monkeypatch.setattr(expiry, "disable_user", disable_user)
        monkeypatch.setattr(expiry.time, "sleep", lambda _seconds: None)

        first_result = expiry.disable_or_delete_user_if_expired()
        second_result = expiry.disable_or_delete_user_if_expired()

        assert first_result == [user_id]
        assert second_result == []
        assert ExpiredUser.query.count() == 1
        assert db.session.get(User, user_id).is_disabled is True
        disable_user.assert_called_once_with(user_id, commit=False)


def test_delete_expired_user_uses_one_transaction(app, session, monkeypatch):
    with app.app_context():
        user = _expired_user()
        session.add(user)
        session.commit()
        user_id = user.id

        monkeypatch.setattr(expiry.time, "sleep", lambda _seconds: None)

        result = expiry.disable_or_delete_user_if_expired()

        assert result == [user_id]
        assert db.session.get(User, user_id) is None
        assert ExpiredUser.query.count() == 1


def test_expired_user_event_is_unique(app, session):
    with app.app_context():
        expired_at = datetime.datetime.now(datetime.UTC)
        event = {
            "original_user_id": 42,
            "username": "expired-user",
            "expired_at": expired_at,
            "deleted_at": expired_at,
        }

        session.add(ExpiredUser(**event))
        session.commit()
        session.add(ExpiredUser(**event))

        with pytest.raises(IntegrityError):
            session.commit()
