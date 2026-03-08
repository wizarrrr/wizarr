from app.extensions import db
from app.models import AdminAccount, User


def test_process_user_deletion_manual_disable_sends_reason_email(client, app, monkeypatch):
    sent = {}

    with app.app_context():
        admin = AdminAccount(username="ops_admin")
        admin.set_password("Password1")
        db.session.add(admin)

        user = User(
            token="tok-1",
            username="target-user",
            email="target@example.com",
            code="invite-code",
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client.post("/login", data={"username": "ops_admin", "password": "Password1"})

    monkeypatch.setattr("app.blueprints.admin.routes.disable_user", lambda _uid: True)

    def fake_send(event_type, recipient_email, username, expires, reason=None):
        sent.update(
            {
                "event_type": event_type,
                "recipient": recipient_email,
                "username": username,
                "reason": reason,
            }
        )
        return True

    monkeypatch.setattr(
        "app.services.user_email_notifications.send_user_lifecycle_email",
        fake_send,
    )

    response = client.post(
        "/users/process-deletion",
        data={
            "manual_action": "disable",
            "manual_reason": "Payment overdue",
            "server_accounts": str(user_id),
        },
    )

    assert response.status_code == 200

    with app.app_context():
        updated = db.session.get(User, user_id)
        assert updated is not None
        assert updated.is_disabled is True

        assert sent["event_type"] == "user_manually_disabled_notification"
        assert sent["recipient"] == "target@example.com"
        assert sent["reason"] == "Payment overdue"

        db.session.delete(updated)
        admin = AdminAccount.query.filter_by(username="ops_admin").first()
        if admin:
            db.session.delete(admin)
        db.session.commit()
