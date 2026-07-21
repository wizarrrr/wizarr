from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models import ExternalEnrollmentState, Invitation


def utc_now_naive():
    return datetime.now(UTC).replace(tzinfo=None)


def create_external_invitation(db_session, **overrides):
    """Create an external enrollment invitation for callback route tests."""
    values = {
        "code": "ABC123",
        "used": False,
        "unlimited": False,
        "expires": None,
        "account_creation_mode": "external",
        "external_enrollment_provider": "static_url",
        "external_enrollment_url": "https://idp.example/enroll",
        "external_enrollment_append_context": True,
    }
    values.update(overrides)

    invitation = Invitation(**values)
    db_session.add(invitation)
    db_session.commit()
    return invitation


def create_pending_external_enrollment(db_session, invitation, **overrides):
    """Store pending external enrollment state in the database."""
    values = {
        "invitation": invitation,
        "state": f"state-{uuid4().hex}",
        "provider": "static_url",
        "callback_url": "http://localhost/invitation/external/callback",
        "expires_at": utc_now_naive() + timedelta(minutes=30),
    }
    values.update(overrides)

    pending = ExternalEnrollmentState(**values)
    db_session.add(pending)
    db_session.commit()
    return pending


def test_external_enrollment_callback_resumes_post_wizard(
    client,
    session,
    monkeypatch,
):
    """Test that a valid external enrollment callback grants wizard access."""
    monkeypatch.setenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", "X-Test-User")
    invitation = create_external_invitation(session)
    pending = create_pending_external_enrollment(session, invitation)

    response = client.get(
        f"/invitation/external/callback?state={pending.state}",
        headers={"X-Test-User": "leo"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/wizard/post-wizard/0")

    with client.session_transaction() as flask_session:
        assert flask_session["wizard_access"] == "ABC123"
        assert flask_session["invitation_in_progress"] is True
        assert flask_session["external_enrollment_user"] == {"subject": "leo"}
        assert "external_enrollment_state" not in flask_session
        assert "external_enrollment" not in flask_session

    session.expire_all()
    consumed = session.get(ExternalEnrollmentState, pending.id)

    assert consumed.consumed_at is not None
    assert consumed.external_subject == "leo"


def test_external_enrollment_callback_requires_pending_state(client, monkeypatch):
    """Test that callbacks without pending external enrollment state are rejected."""
    monkeypatch.setenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", "X-Test-User")

    response = client.get(
        "/invitation/external/callback?state=state-token",
        headers={"X-Test-User": "leo"},
    )

    assert response.status_code == 400


def test_external_enrollment_callback_requires_state_query_param(client, monkeypatch):
    """Test that callbacks without a state query parameter are rejected."""
    monkeypatch.setenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", "X-Test-User")

    response = client.get(
        "/invitation/external/callback",
        headers={"X-Test-User": "leo"},
    )

    assert response.status_code == 400


def test_external_enrollment_callback_rejects_invalid_state(
    client,
    session,
    monkeypatch,
):
    """Test that callbacks with an invalid state do not grant wizard access."""
    monkeypatch.setenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", "X-Test-User")
    invitation = create_external_invitation(session)
    pending = create_pending_external_enrollment(session, invitation)

    response = client.get(
        f"/invitation/external/callback?state=wrong-{pending.state}",
        headers={"X-Test-User": "leo"},
    )

    assert response.status_code == 400

    with client.session_transaction() as flask_session:
        assert "wizard_access" not in flask_session

    session.expire_all()
    unchanged = session.get(ExternalEnrollmentState, pending.id)

    assert unchanged.consumed_at is None
    assert unchanged.external_subject is None


def test_external_enrollment_callback_rejects_expired_state(
    client,
    session,
    monkeypatch,
):
    """Test that expired external enrollment states are rejected and consumed."""
    monkeypatch.setenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", "X-Test-User")
    invitation = create_external_invitation(session)
    pending = create_pending_external_enrollment(
        session,
        invitation,
        expires_at=utc_now_naive() - timedelta(minutes=1),
    )

    response = client.get(
        f"/invitation/external/callback?state={pending.state}",
        headers={"X-Test-User": "leo"},
    )

    assert response.status_code == 400

    with client.session_transaction() as flask_session:
        assert "wizard_access" not in flask_session

    session.expire_all()
    consumed = session.get(ExternalEnrollmentState, pending.id)

    assert consumed.consumed_at is not None
    assert consumed.external_subject is None


def test_external_enrollment_callback_requires_auth_header_configuration(
    client,
    session,
    monkeypatch,
):
    """Test that callback verification requires an auth header setting."""
    monkeypatch.delenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", raising=False)
    invitation = create_external_invitation(session)
    pending = create_pending_external_enrollment(session, invitation)

    response = client.get(f"/invitation/external/callback?state={pending.state}")

    assert response.status_code == 400

    session.expire_all()
    unchanged = session.get(ExternalEnrollmentState, pending.id)

    assert unchanged.consumed_at is None
    assert unchanged.external_subject is None


def test_external_enrollment_callback_requires_verified_external_user(
    client,
    session,
    monkeypatch,
):
    """Test that callbacks without the configured auth header are rejected."""
    monkeypatch.setenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", "X-Test-User")
    invitation = create_external_invitation(session)
    pending = create_pending_external_enrollment(session, invitation)

    response = client.get(f"/invitation/external/callback?state={pending.state}")

    assert response.status_code == 403

    with client.session_transaction() as flask_session:
        assert "wizard_access" not in flask_session

    session.expire_all()
    unchanged = session.get(ExternalEnrollmentState, pending.id)

    assert unchanged.consumed_at is None
    assert unchanged.external_subject is None


def test_external_enrollment_callback_rejects_expired_invitation(
    client,
    session,
    monkeypatch,
):
    """Test that expired invitations cannot resume after external enrollment."""
    monkeypatch.setenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", "X-Test-User")
    invitation = create_external_invitation(
        session,
        expires=utc_now_naive() - timedelta(days=1),
    )
    pending = create_pending_external_enrollment(session, invitation)

    response = client.get(
        f"/invitation/external/callback?state={pending.state}",
        headers={"X-Test-User": "leo"},
    )

    assert response.status_code == 404

    with client.session_transaction() as flask_session:
        assert "wizard_access" not in flask_session
        assert "external_enrollment_state" not in flask_session
        assert "external_enrollment" not in flask_session

    session.expire_all()
    consumed = session.get(ExternalEnrollmentState, pending.id)

    assert consumed.consumed_at is not None
    assert consumed.external_subject is None