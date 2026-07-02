import datetime

from app.models import Invitation


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


def set_pending_external_enrollment(client, **overrides):
    """Store pending external enrollment state in the Flask session."""
    values = {
        "invite_code": "ABC123",
        "state": "state-token",
        "provider": "static_url",
        "callback_url": "http://localhost/invitation/external/callback",
    }
    values.update(overrides)

    with client.session_transaction() as flask_session:
        flask_session["external_enrollment"] = values


def test_external_enrollment_callback_resumes_post_wizard(
    client,
    session,
    monkeypatch,
):
    """Test that a valid external enrollment callback grants wizard access."""
    monkeypatch.setenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", "X-Test-User")
    create_external_invitation(session)
    set_pending_external_enrollment(client)

    response = client.get(
        "/invitation/external/callback?state=state-token",
        headers={"X-Test-User": "leo"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/wizard/post-wizard/0")

    with client.session_transaction() as flask_session:
        assert flask_session["wizard_access"] == "ABC123"
        assert flask_session["invitation_in_progress"] is True
        assert flask_session["external_enrollment_user"] == {"subject": "leo"}
        assert "external_enrollment" not in flask_session


def test_external_enrollment_callback_requires_pending_session(client, monkeypatch):
    """Test that callbacks without pending external enrollment are rejected."""
    monkeypatch.setenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", "X-Test-User")

    response = client.get(
        "/invitation/external/callback?state=state-token",
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
    create_external_invitation(session)
    set_pending_external_enrollment(client)

    response = client.get(
        "/invitation/external/callback?state=wrong-state",
        headers={"X-Test-User": "leo"},
    )

    assert response.status_code == 400

    with client.session_transaction() as flask_session:
        assert "wizard_access" not in flask_session


def test_external_enrollment_callback_requires_auth_header_configuration(
    client,
    session,
    monkeypatch,
):
    """Test that callback verification requires an auth header setting."""
    monkeypatch.delenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", raising=False)
    create_external_invitation(session)
    set_pending_external_enrollment(client)

    response = client.get("/invitation/external/callback?state=state-token")

    assert response.status_code == 400


def test_external_enrollment_callback_requires_verified_external_user(
    client,
    session,
    monkeypatch,
):
    """Test that callbacks without the configured auth header are rejected."""
    monkeypatch.setenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", "X-Test-User")
    create_external_invitation(session)
    set_pending_external_enrollment(client)

    response = client.get("/invitation/external/callback?state=state-token")

    assert response.status_code == 403

    with client.session_transaction() as flask_session:
        assert "wizard_access" not in flask_session


def test_external_enrollment_callback_rejects_expired_invitation(
    client,
    session,
    monkeypatch,
):
    """Test that expired invitations cannot resume after external enrollment."""
    monkeypatch.setenv("EXTERNAL_ENROLLMENT_AUTH_HEADER", "X-Test-User")
    create_external_invitation(
        session,
        expires=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1),
    )
    set_pending_external_enrollment(client)

    response = client.get(
        "/invitation/external/callback?state=state-token",
        headers={"X-Test-User": "leo"},
    )

    assert response.status_code == 404

    with client.session_transaction() as flask_session:
        assert "wizard_access" not in flask_session
        assert "external_enrollment" not in flask_session
