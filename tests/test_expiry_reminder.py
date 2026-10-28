"""Tests for the expiry-reminder query and the scheduled reminder job."""

import datetime
from unittest.mock import patch

import pytest

from app.extensions import db
from app.models import SMTPConfiguration, User
from app.services.email import EmailSendError
from app.services.expiry import get_users_needing_reminder
from app.tasks.maintenance import send_expiry_reminders


def _user(session, *, expires_in_days, email="user@example.com", reminded=False):
    user = User(
        token=f"tok-{id(object())}",
        username="user",
        email=email,
        code="CODE",
        expires=datetime.datetime.now(datetime.UTC)
        + datetime.timedelta(days=expires_in_days),
        expiry_reminder_sent_at=(
            datetime.datetime.now(datetime.UTC) if reminded else None
        ),
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def smtp_config(session):
    config = SMTPConfiguration(
        enabled=True,
        host="smtp.example.com",
        port=587,
        encryption="none",
        from_email="wizarr@example.com",
        reminder_days_before=3,
    )
    session.add(config)
    session.commit()
    yield config
    SMTPConfiguration.query.delete()
    session.commit()


def test_get_users_needing_reminder_filters_by_window(session):
    within_window = _user(session, expires_in_days=2)
    outside_window = _user(session, expires_in_days=10)
    already_expired = _user(session, expires_in_days=-1)
    already_reminded = _user(session, expires_in_days=1, reminded=True)
    no_email = _user(session, expires_in_days=1, email=None)

    result = get_users_needing_reminder(3)

    ids = {u.id for u in result}
    assert within_window.id in ids
    assert outside_window.id not in ids
    assert already_expired.id not in ids
    assert already_reminded.id not in ids
    assert no_email.id not in ids


def test_get_users_needing_reminder_zero_days_returns_nothing(session):
    _user(session, expires_in_days=1)

    assert get_users_needing_reminder(0) == []


def test_send_expiry_reminders_noop_when_smtp_disabled(app, session):
    _user(session, expires_in_days=1)

    with patch("app.services.email.send_expiry_reminder_email") as send:
        send_expiry_reminders(app)

    send.assert_not_called()


def test_send_expiry_reminders_sends_and_marks_user(app, smtp_config, session):
    user_id = _user(session, expires_in_days=1).id
    sent_to_ids = []

    with patch(
        "app.services.email.send_expiry_reminder_email",
        side_effect=lambda user, _days_left: sent_to_ids.append(user.id),
    ):
        send_expiry_reminders(app)

    assert sent_to_ids == [user_id]
    assert db.session.get(User, user_id).expiry_reminder_sent_at is not None


def test_send_expiry_reminders_is_idempotent(app, smtp_config, session):
    _user(session, expires_in_days=1)

    with patch("app.services.email.send_expiry_reminder_email") as send:
        send_expiry_reminders(app)
        send_expiry_reminders(app)

    send.assert_called_once()


def test_send_expiry_reminders_isolates_per_user_failures(app, smtp_config, session):
    failing_id = _user(session, expires_in_days=1, email="fail@example.com").id
    ok_id = _user(session, expires_in_days=2, email="ok@example.com").id

    def _send(user, _days_left):
        if user.id == failing_id:
            raise EmailSendError("boom")

    with patch(
        "app.services.email.send_expiry_reminder_email", side_effect=_send
    ) as send:
        send_expiry_reminders(app)

    assert send.call_count == 2
    assert db.session.get(User, failing_id).expiry_reminder_sent_at is None
    assert db.session.get(User, ok_id).expiry_reminder_sent_at is not None


def test_admin_editing_expiry_resets_reminder_flag(admin_client, session):
    """Editing a user's expiry in the admin UI must reset the reminder flag,
    so a renewed user becomes eligible for a fresh reminder.
    """
    user = _user(session, expires_in_days=1, reminded=True)

    resp = admin_client.post(
        f"/user/{user.id}",
        data={"expires": "2030-01-01T00:00"},
    )

    assert resp.status_code == 200
    assert db.session.get(User, user.id).expiry_reminder_sent_at is None


def test_admin_clearing_expiry_resets_reminder_flag(admin_client, session):
    user = _user(session, expires_in_days=1, reminded=True)

    resp = admin_client.post(f"/user/{user.id}", data={"expires": ""})

    assert resp.status_code == 200
    assert db.session.get(User, user.id).expiry_reminder_sent_at is None
