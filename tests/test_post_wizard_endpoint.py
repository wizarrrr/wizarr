"""
Tests for post-wizard endpoint.

This module tests the /post-wizard endpoint which displays wizard steps
after a user accepts an invitation and creates their account.

Requirements tested:
- 8.1: Redirect to /post-wizard after accepting invitation (if post-invite steps exist)
- 8.2: Redirect to completion page when no post-invite steps exist
- 8.3: Only display post_invite category steps
- 8.4: Match existing wizard interface
- 8.5: Redirect to login when not authenticated
- 8.6: Redirect to join page before accepting invitation
- 8.7: Redirect to completion page after completing all steps
- 8.8: Backward compatibility with /wizard endpoint
- 15.2: Integration tests for post-wizard flow
"""

import pytest

from app.extensions import db
from app.models import AdminAccount, Invitation, MediaServer, WizardStep
from app.services.invite_code_manager import InviteCodeManager


@pytest.fixture
def session(app):
    """Return a clean database session inside an app context."""
    with app.app_context():
        # Clean up before the test to ensure fresh state
        db.session.rollback()
        # Delete all test data in correct order (respecting foreign keys)
        db.session.execute(db.text("DELETE FROM invitation_server"))
        db.session.execute(db.text("DELETE FROM invitation_user"))
        db.session.query(WizardStep).delete()
        db.session.query(Invitation).delete()
        db.session.query(MediaServer).delete()
        db.session.query(AdminAccount).delete()
        db.session.commit()

        yield db.session

        # Clean up after the test
        db.session.rollback()
        # Delete all test data in correct order (respecting foreign keys)
        db.session.execute(db.text("DELETE FROM invitation_server"))
        db.session.execute(db.text("DELETE FROM invitation_user"))
        db.session.query(WizardStep).delete()
        db.session.query(Invitation).delete()
        db.session.query(MediaServer).delete()
        db.session.query(AdminAccount).delete()
        db.session.commit()


class TestPostWizardAuthentication:
    """Test authentication requirements for post-wizard endpoint."""

    def test_redirect_to_login_when_not_authenticated(self, app, client):
        """Test that unauthenticated users without wizard_access are redirected."""
        # Try to access post-wizard without authentication or wizard_access
        response = client.get("/wizard/post-wizard", follow_redirects=False)

        # Should redirect (either to login or home depending on auth config)
        assert response.status_code == 302
        assert response.location in ["/login", "/"]

    def test_allow_access_with_wizard_access_session(self, app, client, session):
        """Test that users with wizard_access session can access post-wizard."""
        # Create server
        server = MediaServer(
            name="Test Jellyfin",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_key",
            verified=True,
        )
        session.add(server)
        session.flush()

        # Create invitation and post-invite step
        invitation = Invitation(code="TEST123", unlimited=True)
        invitation.servers = [server]

        post_step = WizardStep(
            server_type="jellyfin",
            category="post_invite",
            position=0,
            markdown="# Welcome",
        )

        session.add_all([invitation, post_step])
        session.commit()

        # Set wizard_access session
        with client.session_transaction() as sess:
            sess["wizard_access"] = "TEST123"

        # Access post-wizard
        response = client.get("/wizard/post-wizard")

        assert response.status_code == 200
        assert b"Welcome" in response.data


class TestPostWizardStepFiltering:
    """Test that post-wizard only shows post_invite category steps."""

    def test_only_display_post_invite_steps(self, app, client, session):
        """Test that only post_invite category steps are displayed."""
        # Create server
        server = MediaServer(
            name="Test Jellyfin",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_key",
            verified=True,
        )
        session.add(server)
        session.flush()

        # Create invitation
        invitation = Invitation(code="TEST123", unlimited=True)
        invitation.servers.append(server)

        # Create both pre and post-invite steps
        pre_step = WizardStep(
            server_type="jellyfin",
            category="pre_invite",
            position=0,
            markdown="# Pre-invite step",
        )

        post_step = WizardStep(
            server_type="jellyfin",
            category="post_invite",
            position=0,
            markdown="# Post-invite step",
        )

        session.add_all([invitation, pre_step, post_step])
        session.commit()

        # Set wizard_access session
        with client.session_transaction() as sess:
            sess["wizard_access"] = "TEST123"

        # Access post-wizard
        response = client.get("/wizard/post-wizard")

        assert response.status_code == 200
        # Should show post-invite step
        assert b"Post-invite step" in response.data
        # Should NOT show pre-invite step
        assert b"Pre-invite step" not in response.data


class TestPostWizardCompletion:
    """Test completion behavior when no steps exist or all steps are completed."""

    def test_redirect_to_completion_when_no_post_invite_steps(
        self, app, client, session
    ):
        """Test redirect to completion page when no post-invite steps exist."""
        # Delete all wizard steps to ensure none exist
        session.query(WizardStep).delete()
        session.commit()

        # Create server
        server = MediaServer(
            name="Test Jellyfin",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_key",
            verified=True,
        )
        session.add(server)
        session.flush()

        # Create invitation without post-invite steps
        invitation = Invitation(code="TEST123", unlimited=True)
        invitation.servers.append(server)

        session.add(invitation)
        session.commit()

        # Set wizard_access session
        with client.session_transaction() as sess:
            sess["wizard_access"] = "TEST123"

        # Access post-wizard
        response = client.get("/wizard/post-wizard", follow_redirects=False)

        assert response.status_code == 302
        # Should redirect to completion page
        assert response.location == "/wizard/complete"

    def test_clear_invite_data_on_completion(self, app, client, session):
        """Test that invite data is cleared when no post-invite steps exist."""
        # Delete all wizard steps to ensure none exist
        session.query(WizardStep).delete()
        session.commit()

        # Create server
        server = MediaServer(
            name="Test Jellyfin",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_key",
            verified=True,
        )
        session.add(server)
        session.flush()

        # Create invitation without post-invite steps
        invitation = Invitation(code="TEST123", unlimited=True)
        invitation.servers.append(server)

        session.add(invitation)
        session.commit()

        # Set wizard_access and invite code
        with client.session_transaction() as sess:
            sess["wizard_access"] = "TEST123"
            sess[InviteCodeManager.STORAGE_KEY] = "TEST123"

        # Access post-wizard (should redirect and clear data)
        client.get("/wizard/post-wizard", follow_redirects=True)

        # Verify invite data is cleared
        with client.session_transaction() as sess:
            assert sess.get(InviteCodeManager.STORAGE_KEY) is None
            assert "wizard_access" not in sess

    def test_clear_invite_data_after_completing_all_steps(self, app, client, session):
        """Test that invite data is cleared after completing all post-wizard steps."""
        # Delete all wizard steps first
        session.query(WizardStep).delete()
        session.commit()

        # Create server
        server = MediaServer(
            name="Test Jellyfin",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_key",
            verified=True,
        )
        session.add(server)
        session.flush()

        # Create invitation with one post-invite step
        invitation = Invitation(code="TEST123", unlimited=True)
        invitation.servers.append(server)

        post_step = WizardStep(
            server_type="jellyfin",
            category="post_invite",
            position=0,
            markdown="# Final step",
        )

        session.add_all([invitation, post_step])
        session.commit()

        # Set wizard_access and invite code
        with client.session_transaction() as sess:
            sess["wizard_access"] = "TEST123"
            sess[InviteCodeManager.STORAGE_KEY] = "TEST123"

        # Access last step with "next" direction (completing wizard)
        response = client.get("/wizard/post-wizard/0?dir=next", follow_redirects=False)

        assert response.status_code == 302
        assert response.location == "/wizard/complete"

        # Follow redirect to completion page to verify data is cleared
        response = client.get("/wizard/complete", follow_redirects=False)
        assert response.status_code == 302  # Redirects to home page

        # Verify invite data is cleared after visiting completion page
        with client.session_transaction() as sess:
            assert sess.get(InviteCodeManager.STORAGE_KEY) is None
            assert "wizard_access" not in sess


class TestPostWizardServerTypeResolution:
    """Test server type resolution from invitation and fallback logic."""

    def test_get_server_type_from_invitation(self, app, client, session):
        """Test that server type is correctly determined from invitation."""
        # Create server
        server = MediaServer(
            name="Test Jellyfin",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_key",
            verified=True,
        )
        session.add(server)
        session.flush()

        # Create invitation
        invitation = Invitation(code="TEST123", unlimited=True)
        invitation.servers.append(server)

        post_step = WizardStep(
            server_type="jellyfin",
            category="post_invite",
            position=0,
            markdown="# Jellyfin step",
        )

        session.add_all([invitation, post_step])
        session.commit()

        # Set wizard_access session
        with client.session_transaction() as sess:
            sess["wizard_access"] = "TEST123"

        # Access post-wizard
        response = client.get("/wizard/post-wizard")

        assert response.status_code == 200
        assert b"Jellyfin step" in response.data

    def test_fallback_to_first_server_when_no_invitation(self, app, client, session):
        """Test fallback to first configured server when no invitation context."""
        # Create server
        server = MediaServer(
            name="Test Plex",
            server_type="plex",
            url="http://localhost:32400",
            api_key="test_key",
            verified=True,
        )
        session.add(server)
        session.flush()

        # Create post-invite step for plex
        post_step = WizardStep(
            server_type="plex",
            category="post_invite",
            position=0,
            markdown="# Plex step",
        )

        session.add(post_step)
        session.commit()

        # Set wizard_access session without valid invitation
        with client.session_transaction() as sess:
            sess["wizard_access"] = "INVALID"

        # Access post-wizard (should fallback to first server)
        response = client.get("/wizard/post-wizard")

        assert response.status_code == 200
        assert b"Plex step" in response.data

    def test_error_when_no_servers_configured(self, app, client, session):
        """Test error message when no media servers are configured."""
        # Clean up any seeded wizard steps
        session.query(WizardStep).delete()
        session.query(MediaServer).delete()
        session.commit()

        # Set wizard_access session
        with client.session_transaction() as sess:
            sess["wizard_access"] = "TEST123"

        # Access post-wizard without any servers configured
        response = client.get("/wizard/post-wizard", follow_redirects=False)

        assert response.status_code == 302
        assert response.location == "/"


class TestPostWizardNavigation:
    """Test navigation through post-wizard steps."""

    def test_navigate_through_multiple_steps(self, app, client, session):
        """Test navigating through multiple post-wizard steps."""
        # Create server
        server = MediaServer(
            name="Test Jellyfin",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_key",
            verified=True,
        )
        session.add(server)
        session.flush()

        # Create invitation with multiple post-invite steps
        invitation = Invitation(code="TEST123", unlimited=True)
        invitation.servers.append(server)

        step1 = WizardStep(
            server_type="jellyfin",
            category="post_invite",
            position=0,
            markdown="# Step 1",
        )

        step2 = WizardStep(
            server_type="jellyfin",
            category="post_invite",
            position=1,
            markdown="# Step 2",
        )

        session.add_all([invitation, step1, step2])
        session.commit()

        # Set wizard_access session
        with client.session_transaction() as sess:
            sess["wizard_access"] = "TEST123"

        # Access first step
        response = client.get("/wizard/post-wizard/0")
        assert response.status_code == 200
        assert b"Step 1" in response.data

        # Navigate to second step
        response = client.get("/wizard/post-wizard/1")
        assert response.status_code == 200
        assert b"Step 2" in response.data

    def test_htmx_next_step_returns_partial_response(self, app, client, session):
        """Ensure HTMX navigation returns the next step instead of redirecting."""

        server = MediaServer(
            name="Test Jellyfin",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_key",
            verified=True,
        )
        session.add(server)
        session.flush()

        invitation = Invitation(code="TEST123", unlimited=True)
        invitation.servers.append(server)

        step1 = WizardStep(
            server_type="jellyfin",
            category="post_invite",
            position=0,
            markdown="# Step 1",
        )

        step2 = WizardStep(
            server_type="jellyfin",
            category="post_invite",
            position=1,
            markdown="# Step 2",
        )

        session.add_all([invitation, step1, step2])
        session.commit()

        with client.session_transaction() as sess:
            sess["wizard_access"] = "TEST123"

        # Prime the wizard by loading the first step
        initial_response = client.get("/wizard/post-wizard/0")
        assert initial_response.status_code == 200
        assert b"Step 1" in initial_response.data

        response = client.get(
            "/wizard/post-wizard/1",
            query_string={"dir": "next"},
            headers={"HX-Request": "true"},
        )

        assert response.status_code == 200
        assert response.headers.get("X-Wizard-Idx") == "1"
        assert response.headers.get("HX-Redirect") is None
        assert b"Step 2" in response.data
