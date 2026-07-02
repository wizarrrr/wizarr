import datetime
from urllib.parse import parse_qs, urlsplit

from app.models import Invitation


def create_external_invitation(db_session, **overrides):
    """Create an external enrollment invitation for route tests."""
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


def test_external_enrollment_start_redirects_to_provider_url(client, session):
    """Test that external enrollment redirects to the configured provider URL."""
    create_external_invitation(session)

    response = client.get("/invitation/external/start/ABC123")

    assert response.status_code == 302

    location = response.headers["Location"]
    parts = urlsplit(location)
    query = parse_qs(parts.query)

    assert parts.scheme == "https"
    assert parts.netloc == "idp.example"
    assert parts.path == "/enroll"
    assert query["source"] == ["wizarr"]
    assert query["invite_code"] == ["ABC123"]
    assert query["callback_url"][0].endswith("/invitation/external/callback")
    assert query["state"][0]

    with client.session_transaction() as flask_session:
        pending = flask_session["external_enrollment"]

    assert pending["invite_code"] == "ABC123"
    assert pending["state"] == query["state"][0]
    assert pending["provider"] == "static_url"
    assert pending["callback_url"].endswith("/invitation/external/callback")


def test_external_enrollment_start_rejects_builtin_invitation(client, session):
    """Test that built-in account creation invitations cannot start external enrollment."""
    create_external_invitation(
        session,
        account_creation_mode="wizarr",
    )

    response = client.get("/invitation/external/start/ABC123")

    assert response.status_code == 400


def test_external_enrollment_start_rejects_used_invitation(client, session):
    """Test that used single-use invitations cannot start external enrollment."""
    create_external_invitation(
        session,
        used=True,
        unlimited=False,
    )

    response = client.get("/invitation/external/start/ABC123")

    assert response.status_code == 404


def test_external_enrollment_start_rejects_expired_invitation(client, session):
    """Test that expired invitations cannot start external enrollment."""
    create_external_invitation(
        session,
        expires=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1),
    )

    response = client.get("/invitation/external/start/ABC123")

    assert response.status_code == 404


def test_external_enrollment_start_requires_provider_url(client, session):
    """Test that external enrollment start rejects invitations without a provider URL."""
    create_external_invitation(
        session,
        external_enrollment_url=None,
    )

    response = client.get("/invitation/external/start/ABC123")

    assert response.status_code == 400

    with client.session_transaction() as flask_session:
        assert "external_enrollment" not in flask_session
