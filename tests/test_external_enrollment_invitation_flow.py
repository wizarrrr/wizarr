from app.extensions import db
from app.models import Invitation, MediaServer
from app.services.invitation_flow import InvitationFlowManager
from app.services.invitation_flow.results import ProcessingStatus


def create_media_server():
    """Create a media server so invitation flow has a target server."""
    server = MediaServer(
        name="Test Jellyfin",
        server_type="jellyfin",
        url="http://jellyfin.local",
        api_key="test-key",
    )
    db.session.add(server)
    db.session.commit()
    return server


def create_invitation(server, **overrides):
    """Create an invitation for invitation flow tests."""
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
    invitation.servers.append(server)
    db.session.add(invitation)
    db.session.commit()
    return invitation


def test_external_invitation_display_redirects_to_external_enrollment(app, session):
    """Test that external invitations redirect to external enrollment after pre-steps."""
    server = create_media_server()
    create_invitation(server)

    with app.test_request_context("/j/ABC123"):
        result = InvitationFlowManager().process_invitation_display("ABC123")

    assert result.status == ProcessingStatus.REDIRECT_REQUIRED
    assert result.redirect_url == "/invitation/external/start/ABC123"
    assert result.session_data["invitation_in_progress"] is True


def test_builtin_invitation_display_uses_regular_workflow(app, session):
    """Test that built-in invitations still use the regular invitation workflow."""
    server = create_media_server()
    create_invitation(
        server,
        account_creation_mode="wizarr",
    )

    with app.test_request_context("/j/ABC123"):
        result = InvitationFlowManager().process_invitation_display("ABC123")

    assert result.status != ProcessingStatus.REDIRECT_REQUIRED
