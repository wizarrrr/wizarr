from datetime import UTC, datetime

from app.extensions import db
from app.models import Notification
from app.services.user_email_notifications import send_user_lifecycle_email


def test_send_user_created_confirmation_uses_subscribed_smtp_agent(app, monkeypatch):
    sent_payload = {}

    def fake_smtp(
        msg,
        title,
        host,
        port,
        username,
        password,
        from_email,
        to_emails,
        encryption,
        html_message=None,
        return_error=False,
    ):
        sent_payload.update(
            {
                "msg": msg,
                "title": title,
                "host": host,
                "port": port,
                "to_emails": to_emails,
                "encryption": encryption,
                "html_message": html_message,
            }
        )
        return True

    monkeypatch.setattr("app.services.user_email_notifications._smtp", fake_smtp)

    with app.app_context():
        agent = Notification(
            name="smtp lifecycle",
            type="smtp",
            url="smtp.example.com",
            username="smtp-user",
            password="smtp-pass",
            smtp_port=587,
            smtp_from_email="wizarr@example.com",
            smtp_to_emails="ops@example.com",
            smtp_encryption="starttls",
            notification_events="user_created_confirmation",
        )
        db.session.add(agent)
        db.session.commit()

        ok = send_user_lifecycle_email(
            event_type="user_created_confirmation",
            recipient_email="user@example.com",
            username="alice",
            expires=datetime(2026, 3, 8, 12, 0, tzinfo=UTC),
        )

        db.session.delete(agent)
        db.session.commit()

    assert ok is True
    assert sent_payload["to_emails"] == "user@example.com"
    assert sent_payload["host"] == "smtp.example.com"
    assert "alice" in sent_payload["msg"]
    assert "active until" in sent_payload["msg"]
    assert "<h2" in (sent_payload["html_message"] or "")


def test_send_user_expired_email_not_sent_when_not_subscribed(app, monkeypatch):
    sent_calls = {"count": 0}

    def fake_smtp(*args, **kwargs):
        sent_calls["count"] += 1
        return True

    monkeypatch.setattr("app.services.user_email_notifications._smtp", fake_smtp)

    with app.app_context():
        agent = Notification(
            name="smtp lifecycle",
            type="smtp",
            url="smtp.example.com",
            username="smtp-user",
            password="smtp-pass",
            smtp_port=587,
            smtp_from_email="wizarr@example.com",
            smtp_to_emails="ops@example.com",
            smtp_encryption="starttls",
            notification_events="user_created_confirmation",
        )
        db.session.add(agent)
        db.session.commit()

        ok = send_user_lifecycle_email(
            event_type="user_expired_notification",
            recipient_email="user@example.com",
            username="alice",
            expires=datetime(2026, 3, 8, 12, 0, tzinfo=UTC),
        )

        db.session.delete(agent)
        db.session.commit()

    assert ok is False
    assert sent_calls["count"] == 0


def test_send_manual_deleted_email_includes_reason(app, monkeypatch):
    sent_payload = {}

    def fake_smtp(
        msg,
        title,
        host,
        port,
        username,
        password,
        from_email,
        to_emails,
        encryption,
        html_message=None,
        return_error=False,
    ):
        sent_payload["msg"] = msg
        sent_payload["title"] = title
        sent_payload["html"] = html_message
        return True

    monkeypatch.setattr("app.services.user_email_notifications._smtp", fake_smtp)

    with app.app_context():
        agent = Notification(
            name="smtp lifecycle",
            type="smtp",
            url="smtp.example.com",
            username="smtp-user",
            password="smtp-pass",
            smtp_port=587,
            smtp_from_email="wizarr@example.com",
            smtp_to_emails="ops@example.com",
            smtp_encryption="starttls",
            notification_events="user_manually_deleted_notification",
        )
        db.session.add(agent)
        db.session.commit()

        ok = send_user_lifecycle_email(
            event_type="user_manually_deleted_notification",
            recipient_email="user@example.com",
            username="alice",
            expires=datetime(2026, 3, 8, 12, 0, tzinfo=UTC),
            reason="Terms violation",
        )

        db.session.delete(agent)
        db.session.commit()

    assert ok is True
    assert "Terms violation" in sent_payload["msg"]
    assert "deleted" in sent_payload["title"].lower()
    assert "Terms violation" in (sent_payload["html"] or "")
