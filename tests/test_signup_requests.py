from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.extensions import db
from app.models import Invitation, MediaServer, Settings, SignupRequest, User
from app.services.signup import approve_request, send_approval, submit_request


@pytest.fixture
def signup_setup(session, monkeypatch, app):
    monkeypatch.setitem(app.config, "SIGNUP_PUBLIC_URL", "https://join.example.com")
    session.add(Settings(key="public_signup_enabled", value="true"))
    server = MediaServer(
        name="Family Jellyfin",
        server_type="jellyfin",
        url="http://jellyfin:8096",
        api_key="test-key",
        verified=True,
        allow_downloads=True,
    )
    session.add(server)
    session.commit()
    return server


def test_public_signup_is_disabled_by_default(client, session):
    assert client.get("/signup").status_code == 404
    assert (
        client.post(
            "/signup", data={"name": "Friend", "email": "friend@example.com"}
        ).status_code
        == 404
    )
    assert SignupRequest.query.count() == 0


def test_public_root_offers_signup_only_when_enabled(client, signup_setup):
    db.session.add(Settings(key="admin_username", value="owner"))
    db.session.commit()
    assert client.get("/").location == "/signup"
    Settings.query.filter_by(key="public_signup_enabled").one().value = "false"
    db.session.commit()
    assert client.get("/").location == "/admin"


def test_signup_never_provisions_account(client, signup_setup):
    with patch("app.blueprints.signup.routes.notify_owner") as notice:
        response = client.post(
            "/signup",
            data={"name": "Friend", "email": "friend@example.com", "message": "Family"},
        )
    assert response.status_code == 303
    assert SignupRequest.query.one().status == "pending"
    assert User.query.count() == 0
    assert Invitation.query.count() == 0
    notice.assert_called_once()
    assert client.get(response.location).headers["Cache-Control"] == "no-store"


def test_duplicate_response_does_not_disclose_email(client, signup_setup):
    with patch("app.blueprints.signup.routes.notify_owner") as notice:
        first = client.post(
            "/signup", data={"name": "Friend", "email": "Friend@example.com"}
        )
        second = client.post(
            "/signup", data={"name": "Other", "email": "friend@example.com"}
        )
    assert first.status_code == second.status_code == 303
    assert first.location == second.location
    assert SignupRequest.query.count() == 1
    notice.assert_called_once()


@pytest.mark.parametrize(
    "data",
    [
        {"name": "Friend", "email": "bad"},
        {"name": "", "email": "friend@example.com"},
        {"name": "x" * 101, "email": "friend@example.com"},
    ],
)
def test_invalid_signup_rejected(client, signup_setup, data):
    assert client.post("/signup", data=data).status_code == 400
    assert SignupRequest.query.count() == 0


def test_honeypot_is_ignored(client, signup_setup):
    assert (
        client.post(
            "/signup",
            data={"name": "Bot", "email": "bot@example.com", "website": "spam"},
        ).status_code
        == 303
    )
    assert SignupRequest.query.count() == 0


def test_durable_per_source_limit(client, signup_setup):
    with patch("app.blueprints.signup.routes.notify_owner"):
        for n in range(5):
            assert (
                client.post(
                    "/signup",
                    data={"name": "Friend", "email": f"friend{n}@example.com"},
                ).status_code
                == 303
            )
        assert (
            client.post(
                "/signup", data={"name": "Friend", "email": "extra@example.com"}
            ).status_code
            == 429
        )
    assert SignupRequest.query.count() == 5
    assert SignupRequest.query.first().source_hash != "127.0.0.1"


def test_reviews_require_login_and_post(client, signup_setup):
    item = submit_request("Friend", "friend@example.com", "", "127.0.0.1")
    assert client.get("/admin/signups").status_code == 302
    assert (
        client.post(
            f"/admin/signups/{item.id}/approve", data={"server_id": signup_setup.id}
        ).status_code
        == 302
    )
    assert client.get(f"/admin/signups/{item.id}/approve").status_code == 405
    assert Invitation.query.count() == 0


def test_approval_generates_one_expiring_invite(admin_client, signup_setup):
    item = submit_request("Friend", "friend@example.com", "", "127.0.0.1")
    with patch("app.services.signup._send_email") as mail:
        response = admin_client.post(
            f"/admin/signups/{item.id}/approve", data={"server_id": signup_setup.id}
        )
        admin_client.post(
            f"/admin/signups/{item.id}/approve", data={"server_id": signup_setup.id}
        )
    assert response.status_code == 303
    db.session.refresh(item)
    assert item.status == "approved" and item.email_sent_at
    assert Invitation.query.count() == 1
    assert item.invitation.unlimited is False
    assert item.invitation.allow_downloads is True
    assert item.invitation.servers == [signup_setup]
    assert item.invitation.expires is not None
    assert User.query.count() == 0
    mail.assert_called_once()
    assert mail.call_args.args[0] == "friend@example.com"


def test_rejection_cannot_be_approved(admin_client, signup_setup):
    item = submit_request("Friend", "friend@example.com", "", "127.0.0.1")
    admin_client.post(f"/admin/signups/{item.id}/reject")
    with patch("app.services.signup._send_email") as mail:
        admin_client.post(
            f"/admin/signups/{item.id}/approve", data={"server_id": signup_setup.id}
        )
    db.session.refresh(item)
    assert item.status == "rejected"
    assert Invitation.query.count() == 0
    mail.assert_not_called()


def test_email_failure_preserves_approval_and_can_retry(admin_client, signup_setup):
    item = submit_request("Friend", "friend@example.com", "", "127.0.0.1")
    with patch("app.services.signup._send_email", side_effect=OSError):
        admin_client.post(
            f"/admin/signups/{item.id}/approve", data={"server_id": signup_setup.id}
        )
    db.session.refresh(item)
    assert item.status == "approved" and not item.email_sent_at
    with patch("app.services.signup._send_email") as mail:
        admin_client.post(f"/admin/signups/{item.id}/resend")
    assert Invitation.query.count() == 1
    mail.assert_called_once()


def test_resend_pending_does_not_issue_invite(admin_client, signup_setup):
    item = submit_request("Friend", "friend@example.com", "", "127.0.0.1")
    with patch("app.services.signup._send_email") as mail:
        admin_client.post(f"/admin/signups/{item.id}/resend")
    assert Invitation.query.count() == 0
    mail.assert_not_called()


def test_csrf_blocks_public_and_admin_mutations(app, admin_client, signup_setup):
    item = submit_request("Friend", "friend@example.com", "", "127.0.0.1")
    before = app.config["WTF_CSRF_ENABLED"]
    app.config["WTF_CSRF_ENABLED"] = True
    try:
        assert (
            admin_client.post(
                "/signup", data={"name": "Friend", "email": "new@example.com"}
            ).status_code
            == 400
        )
        assert (
            admin_client.post(
                f"/admin/signups/{item.id}/approve", data={"server_id": signup_setup.id}
            ).status_code
            == 400
        )
        assert admin_client.post(f"/admin/signups/{item.id}/reject").status_code == 400
        assert (
            admin_client.post("/admin/signups", data={"enabled": "y"}).status_code
            == 400
        )
    finally:
        app.config["WTF_CSRF_ENABLED"] = before
    assert Invitation.query.count() == 0


def test_unverified_server_cannot_receive_approval(signup_setup):
    item = submit_request("Friend", "friend@example.com", "", "127.0.0.1")
    signup_setup.verified = False
    db.session.commit()
    with pytest.raises(ValueError):
        approve_request(item.id, signup_setup.id, "owner")
    assert Invitation.query.count() == 0


def test_expired_or_used_invite_cannot_be_emailed(signup_setup):
    item = submit_request("Friend", "friend@example.com", "", "127.0.0.1")
    approve_request(item.id, signup_setup.id, "owner")
    item.invitation.expires = datetime.now(UTC) - timedelta(days=1)
    db.session.commit()
    with patch("app.services.signup._send_email") as mail, pytest.raises(ValueError):
        send_approval(item)
    mail.assert_not_called()


def test_admin_view_escapes_user_input(admin_client, signup_setup):
    submit_request(
        "<script>alert(1)</script>",
        "friend@example.com",
        "<img src=x onerror=alert(1)>",
        "127.0.0.1",
    )
    response = admin_client.get("/admin/signups")
    assert response.status_code == 200
    assert b"&lt;script&gt;" in response.data
    assert b"<img src=x" not in response.data


def test_owner_email_failure_keeps_request(client, signup_setup):
    with patch("app.blueprints.signup.routes.notify_owner", side_effect=OSError):
        assert (
            client.post(
                "/signup", data={"name": "Friend", "email": "friend@example.com"}
            ).status_code
            == 303
        )
    assert SignupRequest.query.one().status == "pending"
