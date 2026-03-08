import json
import subprocess

from app.extensions import db
from app.models import AdminAccount, Notification
from app.services import notifications as notification_service


def test_smtp_starttls_send_success(monkeypatch):
    payload_seen = {}

    def fake_run(command, **kwargs):
        payload_seen.update(json.loads(kwargs["input"]))
        return subprocess.CompletedProcess(command, 0, stdout='{"ok":true}\n')

    monkeypatch.setattr(notification_service.shutil, "which", lambda _cmd: "/usr/bin/node")
    monkeypatch.setattr(notification_service.subprocess, "run", fake_run)

    ok = notification_service._smtp(
        msg="hello",
        title="Wizarr",
        host="smtp.example.com",
        port=587,
        username="smtp-user",
        password="smtp-pass",
        from_email="wizarr@example.com",
        to_emails="admin@example.com",
        encryption="starttls",
    )

    assert ok is True
    assert payload_seen["host"] == "smtp.example.com"
    assert payload_seen["port"] == 587
    assert payload_seen["encryption"] == "starttls"
    assert payload_seen["username"] == "smtp-user"
    assert payload_seen["fromEmail"] == "wizarr@example.com"
    assert payload_seen["toEmails"] == ["admin@example.com"]


def test_smtp_ssl_send_success(monkeypatch):
    payload_seen = {}

    def fake_run(command, **kwargs):
        payload_seen.update(json.loads(kwargs["input"]))
        return subprocess.CompletedProcess(command, 0, stdout='{"ok":true}\n')

    monkeypatch.setattr(notification_service.shutil, "which", lambda _cmd: "/usr/bin/node")
    monkeypatch.setattr(notification_service.subprocess, "run", fake_run)

    ok = notification_service._smtp(
        msg="hello",
        title="Wizarr",
        host="smtps://mail.example.com:465",
        port=None,
        username="smtp-user",
        password="smtp-pass",
        from_email="wizarr@example.com",
        to_emails="admin@example.com,ops@example.com",
        encryption=None,
    )

    assert ok is True
    assert payload_seen["host"] == "mail.example.com"
    assert payload_seen["port"] == 465
    assert payload_seen["encryption"] == "ssl"


def test_smtp_accepts_host_port_input(monkeypatch):
    payload_seen = {}

    def fake_run(command, **kwargs):
        payload_seen.update(json.loads(kwargs["input"]))
        return subprocess.CompletedProcess(command, 0, stdout='{"ok":true}\n')

    monkeypatch.setattr(notification_service.shutil, "which", lambda _cmd: "/usr/bin/node")
    monkeypatch.setattr(notification_service.subprocess, "run", fake_run)

    ok = notification_service._smtp(
        msg="hello",
        title="Wizarr",
        host="smtp.example.com:587",
        port=None,
        username=None,
        password=None,
        from_email="wizarr@example.com",
        to_emails="admin@example.com",
        encryption="tls",
    )

    assert ok is True
    assert payload_seen["host"] == "smtp.example.com"
    assert payload_seen["port"] == 587
    assert payload_seen["encryption"] == "starttls"


def test_notify_dispatches_smtp_for_subscribed_event(app, monkeypatch):
    sent = {"count": 0}

    def fake_smtp(*args, **kwargs):
        sent["count"] += 1
        return True

    monkeypatch.setattr(notification_service, "_smtp", fake_smtp)

    with app.app_context():
        agent = Notification(
            name="smtp dispatch",
            type="smtp",
            url="smtp.example.com",
            username="smtp-user",
            password="smtp-pass",
            smtp_port=587,
            smtp_from_email="wizarr@example.com",
            smtp_to_emails="admin@example.com",
            smtp_encryption="starttls",
            notification_events="user_joined",
        )
        db.session.add(agent)
        db.session.commit()

        notification_service.notify(
            title="User joined",
            message="A user joined",
            tags="tada",
            event_type="user_joined",
        )

        db.session.delete(agent)
        db.session.commit()

    assert sent["count"] == 1


def test_create_smtp_notification_agent(client, app, monkeypatch):
    with app.app_context():
        admin = AdminAccount(username="smtp_admin")
        admin.set_password("Password1")
        db.session.add(admin)
        db.session.commit()

    client.post("/login", data={"username": "smtp_admin", "password": "Password1"})

    monkeypatch.setattr(
        "app.blueprints.notifications.routes._smtp", lambda *a, **k: (True, None)
    )

    response = client.post(
        "/settings/notifications/create",
        data={
            "name": "SMTP Agent",
            "notification_service": "smtp",
            "url": "smtp.example.com",
            "username": "smtp-user",
            "password": "smtp-pass",
            "smtp_port": "587",
            "smtp_encryption": "starttls",
            "smtp_from_email": "wizarr@example.com",
            "smtp_to_emails": "admin@example.com,ops@example.com",
            "event_user_joined": "user_joined",
        },
    )

    assert response.status_code in {302, 303}

    with app.app_context():
        created = Notification.query.filter_by(name="SMTP Agent").first()
        assert created is not None
        assert created.type == "smtp"
        assert created.smtp_port == 587
        assert created.smtp_encryption == "starttls"
        assert created.smtp_from_email == "wizarr@example.com"
        assert created.smtp_to_emails == "admin@example.com,ops@example.com"

        db.session.delete(created)
        admin = AdminAccount.query.filter_by(username="smtp_admin").first()
        if admin:
            db.session.delete(admin)
        db.session.commit()
