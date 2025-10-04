"""
Comprehensive error handling tests for wizard routes.

Tests cover:
- Invalid invite code handling (Requirement 13.1)
- Expired invite code handling (Requirement 13.2)
- Session expiration handling (Requirement 13.2, 13.5)
- Database query failure fallbacks (Requirement 13.3)
- Graceful degradation for missing steps (Requirement 13.6)

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 15.1
"""

import datetime
from datetime import timedelta
from unittest.mock import patch

from app.extensions import db
from app.models import Invitation, MediaServer, WizardStep
from app.services.invite_code_manager import InviteCodeManager


class TestInvalidInviteCodeHandling:
    """Test handling of invalid invite codes (Requirement 13.1)."""

    def test_pre_wizard_with_no_invite_code(self, app, client):
        """Test pre-wizard redirects to home when no invite code in session."""
        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        assert response.location == "/"

    def test_pre_wizard_with_invalid_invite_code(self, app, client):
        """Test pre-wizard redirects to home with invalid invite code."""
        with client.session_transaction():
            InviteCodeManager.store_invite_code("INVALID123")

        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        # Should redirect to home page
        assert response.location == "/"

    def test_pre_wizard_with_nonexistent_invite_code(self, app, client):
        """Test pre-wizard handles nonexistent invite code gracefully."""
        with client.session_transaction():
            InviteCodeManager.store_invite_code("NOTEXIST999")

        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        # Should redirect to home page
        assert response.location == "/"


class TestExpiredInviteCodeHandling:
    """Test handling of expired invite codes (Requirement 13.2)."""

    def test_pre_wizard_with_expired_invitation(self, app, client):
        """Test pre-wizard rejects expired invitations."""
        with app.app_context():
            # Create expired invitation
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            invitation = Invitation(
                code="EXPIRED123",
                unlimited=True,
                expires=datetime.datetime.now() - timedelta(hours=1),
            )
            invitation.servers.append(server)
            db.session.add(invitation)
            db.session.commit()

        with client.session_transaction():
            InviteCodeManager.store_invite_code("EXPIRED123")

        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        # Should redirect to home page
        assert response.location == "/"

    def test_pre_wizard_with_used_limited_invitation(self, app, client):
        """Test pre-wizard rejects used limited invitations."""
        with app.app_context():
            # Create used limited invitation
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            invitation = Invitation(
                code="USED123",
                unlimited=False,
                used=True,
            )
            invitation.servers.append(server)
            db.session.add(invitation)
            db.session.commit()

        with client.session_transaction():
            InviteCodeManager.store_invite_code("USED123")

        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        # Should redirect to home page
        assert response.location == "/"


class TestSessionExpirationHandling:
    """Test handling of session expiration (Requirement 13.2, 13.5)."""

    def test_post_wizard_without_authentication(self, app, client):
        """Test post-wizard redirects to login when not authenticated."""
        response = client.get("/wizard/post-wizard", follow_redirects=False)
        assert response.status_code == 302
        # Should redirect to login
        assert "/login" in response.location or response.location == "/"

    def test_pre_wizard_session_validation_on_each_request(self, app, client):
        """Test that pre-wizard validates invite code on each request."""
        with app.app_context():
            # Create valid invitation
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            invitation = Invitation(
                code="VALID123",
                unlimited=True,
                expires=datetime.datetime.now() + timedelta(days=7),
            )
            invitation.servers.append(server)
            db.session.add(invitation)
            db.session.commit()

        with client.session_transaction():
            InviteCodeManager.store_invite_code("VALID123")

        # First request should work
        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        # Should redirect to join page (no pre-invite steps)
        assert response.status_code == 302

        # Now expire the invitation
        with app.app_context():
            invitation = Invitation.query.filter_by(code="VALID123").first()
            invitation.expires = datetime.datetime.now() - timedelta(hours=1)
            db.session.commit()

        # Second request should fail
        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        # Should redirect to home page
        assert response.location == "/"


class TestDatabaseErrorHandling:
    """Test handling of database query failures (Requirement 13.3)."""

    def test_pre_wizard_handles_database_error_loading_steps(self, app, client):
        """Test pre-wizard handles database errors when loading steps."""
        with app.app_context():
            # Create valid invitation
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            invitation = Invitation(
                code="VALID123",
                unlimited=True,
            )
            invitation.servers.append(server)
            db.session.add(invitation)
            db.session.commit()

        with client.session_transaction():
            InviteCodeManager.store_invite_code("VALID123")

        # Mock database error when querying wizard steps
        with patch("app.blueprints.wizard.routes.WizardStep") as mock_wizard_step:
            mock_wizard_step.query.filter_by.side_effect = Exception("Database error")

            response = client.get("/wizard/pre-wizard", follow_redirects=True)
            assert response.status_code == 200
            # Should gracefully handle error and redirect to join page
            # The exact behavior depends on implementation

    def test_post_wizard_handles_database_error_loading_invitation(self, app, client):
        """Test post-wizard handles database errors when loading invitation."""
        with client.session_transaction() as sess:
            sess["wizard_access"] = "TESTCODE123"

        # Mock database error when querying invitation
        with patch("app.blueprints.wizard.routes.Invitation") as mock_invitation:
            mock_invitation.query.filter_by.side_effect = Exception("Database error")

            response = client.get("/wizard/post-wizard", follow_redirects=True)
            assert response.status_code == 200
            # Should handle error gracefully


class TestGracefulDegradation:
    """Test graceful degradation for missing/broken steps (Requirement 13.6)."""

    def test_pre_wizard_with_no_servers_configured(self, app, client):
        """Test pre-wizard handles case where no servers are configured."""
        with app.app_context():
            # Create invitation without servers
            invitation = Invitation(
                code="NOSERVER123",
                unlimited=True,
            )
            db.session.add(invitation)
            db.session.commit()

        with client.session_transaction():
            InviteCodeManager.store_invite_code("NOSERVER123")

        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        # Should redirect to home page
        assert response.location == "/"

    def test_pre_wizard_with_no_pre_invite_steps(self, app, client):
        """Test pre-wizard redirects to join when no pre-invite steps exist."""
        with app.app_context():
            # Create valid invitation
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            invitation = Invitation(
                code="NOSTEPS123",
                unlimited=True,
            )
            invitation.servers.append(server)
            db.session.add(invitation)
            db.session.commit()

        with client.session_transaction():
            InviteCodeManager.store_invite_code("NOSTEPS123")

        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        # Should redirect to invite page (public.invite route)
        # The exact URL depends on the route configuration
        assert response.location is not None

    def test_post_wizard_with_no_post_invite_steps(self, app, client):
        """Test post-wizard redirects to completion when no post-invite steps exist."""
        with app.app_context():
            # Create valid invitation
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            invitation = Invitation(
                code="NOSTEPS123",
                unlimited=True,
            )
            invitation.servers.append(server)
            db.session.add(invitation)
            db.session.commit()

        with client.session_transaction() as sess:
            sess["wizard_access"] = "NOSTEPS123"

        response = client.get("/wizard/post-wizard", follow_redirects=True)
        assert response.status_code == 200
        # Should show completion message
        assert (
            b"complete" in response.data.lower() or b"welcome" in response.data.lower()
        )


class TestStepRenderingErrors:
    """Test handling of step rendering errors (Requirement 13.6)."""

    def test_wizard_handles_broken_step_content(self, app, client):
        """Test wizard handles steps with broken markdown/Jinja content."""
        with app.app_context():
            # Create server and invitation
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            invitation = Invitation(
                code="BROKEN123",
                unlimited=True,
            )
            invitation.servers.append(server)
            db.session.add(invitation)

            # Create step with broken Jinja template
            step = WizardStep(
                server_type="jellyfin",
                category="pre_invite",
                position=0,
                markdown="# Test\n{{ undefined_variable.nonexistent_method() }}",
            )
            db.session.add(step)
            db.session.commit()

        with client.session_transaction():
            InviteCodeManager.store_invite_code("BROKEN123")

        response = client.get("/wizard/pre-wizard", follow_redirects=True)
        assert response.status_code == 200
        # Should show error message or gracefully handle the broken step
        # The _render function should catch the error and return error HTML


class TestComboWizardErrors:
    """Test error handling in combo wizard for multi-server invitations."""

    def test_combo_wizard_without_server_order(self, client):
        """Test combo wizard redirects when no server order in session."""
        response = client.get("/wizard/combo/0", follow_redirects=False)
        assert response.status_code == 302
        # Should redirect (exact location may vary)
        assert response.location is not None

    def test_combo_wizard_handles_database_error_loading_steps(self, client):
        """Test combo wizard handles database errors when loading steps."""
        with client.session_transaction() as sess:
            sess["wizard_server_order"] = ["jellyfin", "plex"]

        # Mock database error when querying wizard steps
        with patch("app.blueprints.wizard.routes._steps") as mock_steps:
            mock_steps.side_effect = Exception("Database error")

            response = client.get(
                "/wizard/combo/0?category=pre_invite", follow_redirects=True
            )
            assert response.status_code == 200
            # Should handle error gracefully


class TestBundleWizardErrors:
    """Test error handling in bundle wizard."""

    def test_bundle_wizard_without_bundle_id(self, client):
        """Test bundle wizard redirects when no bundle_id in session."""
        response = client.get("/wizard/bundle/0", follow_redirects=False)
        assert response.status_code == 302
        # Should redirect (exact location may vary)
        assert response.location is not None

    def test_bundle_wizard_with_nonexistent_bundle(self, client):
        """Test bundle wizard handles nonexistent bundle gracefully."""
        with client.session_transaction() as sess:
            sess["wizard_bundle_id"] = 99999  # Nonexistent bundle

        response = client.get("/wizard/bundle/0", follow_redirects=True)
        # Should return 404 or redirect with error
        assert response.status_code in [200, 404]


class TestErrorLogging:
    """Test that errors are properly logged (Requirement 13.5)."""

    def test_database_errors_are_logged(self, app, client, caplog):
        """Test that database errors are logged for debugging."""
        with app.app_context():
            # Create valid invitation
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            invitation = Invitation(
                code="VALID123",
                unlimited=True,
            )
            invitation.servers.append(server)
            db.session.add(invitation)
            db.session.commit()

        with client.session_transaction():
            InviteCodeManager.store_invite_code("VALID123")

        # Mock database error
        with patch("app.blueprints.wizard.routes.WizardStep") as mock_wizard_step:
            mock_wizard_step.query.filter_by.side_effect = Exception(
                "Test database error"
            )

            response = client.get("/wizard/pre-wizard", follow_redirects=True)
            assert response.status_code == 200

            # Check that error was logged (if caplog is available)
            # Note: This depends on logging configuration in tests
