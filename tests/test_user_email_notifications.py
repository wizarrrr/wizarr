import datetime

from app.extensions import db
from app.models import AdminAccount, MediaServer, Settings, User
from app.services.email import send_user_lifecycle_email
from app.services.expiry import disable_or_delete_user_if_expired
from app.services.media.service import delete_user
from app.services.media.client_base import MediaClient


class ActivationTestClient(MediaClient):
    def libraries(self):
        return {}

    def create_user(self, *args, **kwargs):
        return {}

    def update_user(self, *args, **kwargs):
        return {}

    def delete_user(self, *args, **kwargs):
        return {}

    def disable_user(self, user_id: str) -> bool:
        return True

    def enable_user(self, user_id: str) -> bool:
        return True

    def get_user(self, *args, **kwargs):
        return {}

    def list_users(self, *args, **kwargs):
        return []

    def now_playing(self):
        return []

    def statistics(self):
        return {}

    def scan_libraries(self, url=None, token=None):
        return {}

    def _do_join(self, username, password, confirm, email, code):
        self._create_user_with_identity_linking(
            {
                "token": "token-123",
                "username": username,
                "email": email,
                "code": code,
                "server_id": self.server_id,
                "expires": datetime.datetime.now(datetime.UTC)
                + datetime.timedelta(days=14),
            }
        )
        db.session.commit()
        return True, "ok"


def test_send_user_lifecycle_email_renders_message(app, session, monkeypatch):
    captured = {}

    def fake_send(self, message):
        captured["subject"] = message.subject
        captured["html"] = message.html
        captured["body"] = message.body

    monkeypatch.setattr("app.services.email.Mail.send", fake_send)
    monkeypatch.setattr(
        "app.services.email.get_smtp_settings",
        lambda include_password=True: {
            "smtp_enabled": True,
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "mailer",
            "smtp_password": "secret",
            "smtp_from_address": "noreply@example.com",
            "smtp_from_name": "Wizarr",
            "smtp_use_tls": True,
            "smtp_use_ssl": False,
            "smtp_language": "en",
        },
    )

    with app.app_context():
        server = MediaServer(
            name="Test Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key",
        )
        session.add(server)
        session.flush()
        user = User(
            token="user-token",
            username="mailer_user",
            email="mailer@example.com",
            code="MAIL123",
            expires=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=7),
            server_id=server.id,
        )
        session.add(user)
        session.commit()

        assert send_user_lifecycle_email(
            user,
            event_type="activated",
            server_name=server.name,
            expires_at=user.expires,
        )

    assert "Test Server" in captured["subject"]
    assert "mailer@example.com" in captured["html"]
    assert "Expiry Date" in captured["body"]


def test_media_client_join_triggers_activation_email(app, session, monkeypatch):
    email_calls = []

    monkeypatch.setattr(
        "app.services.media.client_base.send_user_lifecycle_email",
        lambda user, **kwargs: email_calls.append((user.username, kwargs)) or True,
    )
    monkeypatch.setattr(
        "app.services.media.client_base.notify",
        lambda *args, **kwargs: None,
    )

    with app.app_context():
        server = MediaServer(
            name="Activation Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key",
        )
        session.add(server)
        session.commit()

        client = ActivationTestClient(media_server=server)
        success, _ = client.join(
            username="new_user",
            password="Password123",
            confirm="Password123",
            email="new@example.com",
            code="JOIN123",
        )

    assert success is True
    assert len(email_calls) == 1
    assert email_calls[0][0] == "new_user"
    assert email_calls[0][1]["event_type"] == "activated"
    assert email_calls[0][1]["server_name"] == "Activation Server"
    assert email_calls[0][1]["expires_at"] is not None


def test_expiry_cleanup_sends_expired_email_when_disabling(app, session, monkeypatch):
    email_calls = []

    monkeypatch.setattr("app.services.expiry.disable_user", lambda _user_id: True)
    monkeypatch.setattr(
        "app.services.expiry.send_user_lifecycle_email",
        lambda user, **kwargs: email_calls.append((user.username, kwargs)) or True,
    )
    monkeypatch.setattr("app.services.expiry.time.sleep", lambda _seconds: None)

    with app.app_context():
        session.add(Settings(key="expiry_action", value="disable"))
        server = MediaServer(
            name="Expiry Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key",
        )
        session.add(server)
        session.flush()
        user = User(
            token="expired-token",
            username="expiring_user",
            email="expired@example.com",
            code="EXP123",
            expires=(
                datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
            ).replace(tzinfo=None),
            server_id=server.id,
        )
        session.add(user)
        session.commit()

        processed = disable_or_delete_user_if_expired()
        user_id = user.id

    assert processed == [user_id]
    assert len(email_calls) == 1
    assert email_calls[0][0] == "expiring_user"
    assert email_calls[0][1]["event_type"] == "expired"
    assert email_calls[0][1]["server_name"] == "Expiry Server"
    assert email_calls[0][1]["action_label"] == "disabled"


def test_mailing_settings_route_renders_for_logged_in_admin(client, app, session):
    with app.app_context():
        admin = AdminAccount(username="mail-admin")
        admin.set_password("Password1")
        session.add(admin)
        session.commit()

        admin_id = admin.id

    with client.session_transaction() as flask_session:
        flask_session["_user_id"] = str(admin_id)

    response = client.get("/settings/mailing", headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert b"User Information & Mailing" in response.data
    assert b"Enable User Lifecycle Emails" in response.data


def test_delete_user_handles_ldap_flag_and_still_deletes(app, session, monkeypatch):
    email_calls = []

    class DummyDeleteClient:
        def delete_user(self, _identifier):
            return True

    monkeypatch.setattr(
        "app.services.media.service.send_user_lifecycle_email",
        lambda user, **kwargs: email_calls.append((user.username, kwargs)) or True,
    )
    monkeypatch.setattr(
        "app.services.media.service.get_client_for_media_server",
        lambda _server: DummyDeleteClient(),
    )
    monkeypatch.setattr(
        "app.services.media.service._delete_from_companion_apps",
        lambda _user: None,
    )

    with app.app_context():
        server = MediaServer(
            name="LDAP Compat Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key",
        )
        session.add(server)
        session.flush()
        user = User(
            token="ldap-compat-token",
            username="ldap_compat_user",
            email="ldap@example.com",
            code="LDAP123",
            server_id=server.id,
        )
        session.add(user)
        session.commit()
        user_id = user.id

        # Simulate upstream LDAP user flag in environments where the model includes it.
        # On this branch, the attribute is not persisted but should still be safely handled.
        user.is_ldap_user = True
        delete_user(user_id)

        assert db.session.get(User, user_id) is None

    assert len(email_calls) == 1
    assert email_calls[0][0] == "ldap_compat_user"
    assert email_calls[0][1]["event_type"] == "deleted"
