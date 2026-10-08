import datetime
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import ExpiredUser, MediaServer, Settings, User
from app.services import expiry
from app.services.media import service as media_service


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


@pytest.mark.parametrize("action", ["disable", "delete", "legacy_delete"])
def test_reenabled_expired_user_reuses_history(app, session, monkeypatch, action):
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
        setting = Settings(key="expiry_action", value="disable")
        session.add_all([user, setting])
        session.commit()
        user_id = user.id
        original_expiry = user.expires
        media_client = Mock()
        media_client.disable_user.return_value = True
        media_client.enable_user.return_value = True
        monkeypatch.setattr(
            media_service, "get_client_for_media_server", lambda _server: media_client
        )
        monkeypatch.setattr(expiry.time, "sleep", lambda _seconds: None)

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
            assert db.session.get(User, user_id).is_disabled is True
            assert media_client.disable_user.call_count == 2
            media_client.delete_user.assert_not_called()
        else:
            assert db.session.get(User, user_id) is None
            media_client.delete_user.assert_called_once()


def test_concurrent_new_history_claim_failure_prevents_media_action(
    app, session, monkeypatch
):
    with app.app_context():
        user = _expired_user()
        session.add(user)
        session.commit()
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
        assert db.session.get(User, user.id) is not None
