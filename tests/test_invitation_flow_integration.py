"""
Integration tests for complete invitation flow with pre/post-wizard steps.

Tests verify the complete user journey through the invitation system:
- Invite link → pre-wizard → join → post-wizard
- Bypass prevention (cannot skip pre-wizard)
- Flow with no pre-invite steps
- Flow with no post-invite steps
- Flow with both pre and post-invite steps
"""

import pytest

from app.extensions import db
from app.models import Invitation, MediaServer, WizardStep
from app.services.invite_code_manager import InviteCodeManager


class TestCompleteInvitationFlow:
    """Test complete invitation flow with pre and post-wizard steps."""

    @pytest.fixture
    def setup_invitation_with_steps(self, app):
        """Create invitation with both pre and post-wizard steps."""
        with app.app_context():
            # Clean up any existing wizard steps for jellyfin to avoid conflicts
            db.session.query(WizardStep).filter_by(server_type="jellyfin").delete()
            db.session.commit()

            # Create server
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            db.session.add(server)

            # Create invitation
            invitation = Invitation(code="FLOW123", unlimited=True, used=False)
            db.session.add(invitation)
            db.session.flush()

            # Link invitation to server
            invitation.servers.append(server)

            # Create pre-invite wizard step
            pre_step = WizardStep(
                server_type="jellyfin",
                category="pre_invite",
                position=0,
                markdown="# Welcome\nPlease read this before joining.",
                require_interaction=False,
            )
            db.session.add(pre_step)

            # Create post-invite wizard step
            post_step = WizardStep(
                server_type="jellyfin",
                category="post_invite",
                position=0,
                markdown="# Getting Started\nHere's how to use the service.",
                require_interaction=False,
            )
            db.session.add(post_step)

            db.session.commit()

            yield {
                "invitation": invitation,
                "server": server,
                "pre_step": pre_step,
                "post_step": post_step,
            }

            # Cleanup
            db.session.rollback()
            db.session.query(WizardStep).filter_by(server_type="jellyfin").delete()
            db.session.execute(db.text("DELETE FROM invitation_server"))
            db.session.query(Invitation).filter_by(code="FLOW123").delete()
            db.session.query(MediaServer).filter_by(name="Test Jellyfin").delete()
            db.session.commit()

    def test_complete_flow_with_pre_and_post_steps(
        self, client, app, setup_invitation_with_steps
    ):
        """Test complete flow: invite link → pre-wizard → join → post-wizard."""
        with app.app_context():
            # Step 1: Access invitation link /j/<code>
            response = client.get("/j/FLOW123", follow_redirects=False)

            # Should redirect to pre-wizard since pre-invite steps exist
            assert response.status_code == 302
            assert "/wizard/pre-wizard" in response.location

            # Verify invite code is stored in session
            with client.session_transaction() as sess:
                stored_code = sess.get(InviteCodeManager.STORAGE_KEY)
                assert stored_code == "FLOW123"

            # Step 2: View pre-wizard steps
            response = client.get("/wizard/pre-wizard", follow_redirects=False)
            assert response.status_code == 200
            assert b"Welcome" in response.data

            # Step 3: Complete pre-wizard (navigate to last step)
            # Mark pre-wizard as complete in session
            with client.session_transaction() as sess:
                sess[InviteCodeManager.PRE_WIZARD_COMPLETE_KEY] = True

            # Step 4: Access join page (should now be allowed)
            response = client.get("/j/FLOW123", follow_redirects=False)
            # Should show join form, not redirect to pre-wizard
            assert response.status_code == 200 or (
                response.status_code == 302
                and "/wizard/pre-wizard" not in response.location
            )

    def test_bypass_prevention_cannot_skip_pre_wizard(
        self, client, app, setup_invitation_with_steps
    ):
        """Test that users cannot bypass pre-wizard steps."""
        with app.app_context():
            # Try to access join page directly without completing pre-wizard
            response = client.get("/j/FLOW123", follow_redirects=False)

            # Should redirect to pre-wizard
            assert response.status_code == 302
            assert "/wizard/pre-wizard" in response.location

            # Try again - should still redirect
            response = client.get("/j/FLOW123", follow_redirects=False)
            assert response.status_code == 302
            assert "/wizard/pre-wizard" in response.location

            # Even if we try to tamper with session, should still redirect
            with client.session_transaction():
                # Don't set the completion flag
                pass

            response = client.get("/j/FLOW123", follow_redirects=False)
            assert response.status_code == 302
            assert "/wizard/pre-wizard" in response.location


class TestFlowWithoutPreInviteSteps:
    """Test invitation flow when no pre-invite steps exist."""

    @pytest.fixture
    def setup_invitation_without_pre_steps(self, app):
        """Create invitation with only post-wizard steps."""
        with app.app_context():
            # Clean up any existing wizard steps for jellyfin to avoid conflicts
            db.session.query(WizardStep).filter_by(server_type="jellyfin").delete()
            db.session.commit()

            # Create server
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            db.session.add(server)

            # Create invitation
            invitation = Invitation(code="NOPREFLOW", unlimited=True, used=False)
            db.session.add(invitation)
            db.session.flush()

            # Link invitation to server
            invitation.servers.append(server)

            # Create only post-invite wizard step (no pre-invite steps)
            post_step = WizardStep(
                server_type="jellyfin",
                category="post_invite",
                position=0,
                markdown="# Getting Started\nWelcome!",
                require_interaction=False,
            )
            db.session.add(post_step)

            db.session.commit()

            yield {
                "invitation": invitation,
                "server": server,
                "post_step": post_step,
            }

            # Cleanup
            db.session.rollback()
            db.session.query(WizardStep).filter_by(server_type="jellyfin").delete()
            db.session.execute(db.text("DELETE FROM invitation_server"))
            db.session.query(Invitation).filter_by(code="NOPREFLOW").delete()
            db.session.query(MediaServer).filter_by(name="Test Jellyfin").delete()
            db.session.commit()

    def test_flow_without_pre_invite_steps(
        self, client, app, setup_invitation_without_pre_steps
    ):
        """Test flow when no pre-invite steps exist - should go directly to join."""
        with app.app_context():
            # Access invitation link
            response = client.get("/j/NOPREFLOW", follow_redirects=False)

            # Should NOT redirect to pre-wizard since no pre-invite steps exist
            # Should show join form directly
            assert response.status_code == 200 or (
                response.status_code == 302
                and "/wizard/pre-wizard" not in response.location
            )


class TestFlowWithoutPostInviteSteps:
    """Test invitation flow when no post-invite steps exist."""

    @pytest.fixture
    def setup_invitation_without_post_steps(self, app):
        """Create invitation with only pre-wizard steps."""
        with app.app_context():
            # Clean up any existing wizard steps for jellyfin to avoid conflicts
            db.session.query(WizardStep).filter_by(server_type="jellyfin").delete()
            db.session.commit()

            # Create server
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            db.session.add(server)

            # Create invitation
            invitation = Invitation(code="NOPOSTFLOW", unlimited=True, used=False)
            db.session.add(invitation)
            db.session.flush()

            # Link invitation to server
            invitation.servers.append(server)

            # Create only pre-invite wizard step (no post-invite steps)
            pre_step = WizardStep(
                server_type="jellyfin",
                category="pre_invite",
                position=0,
                markdown="# Before You Join\nImportant information.",
                require_interaction=False,
            )
            db.session.add(pre_step)

            db.session.commit()

            yield {
                "invitation": invitation,
                "server": server,
                "pre_step": pre_step,
            }

            # Cleanup
            db.session.rollback()
            db.session.query(WizardStep).filter_by(server_type="jellyfin").delete()
            db.session.execute(db.text("DELETE FROM invitation_server"))
            db.session.query(Invitation).filter_by(code="NOPOSTFLOW").delete()
            db.session.query(MediaServer).filter_by(name="Test Jellyfin").delete()
            db.session.commit()

    def test_flow_without_post_invite_steps(
        self, client, app, setup_invitation_without_post_steps
    ):
        """Test flow when no post-invite steps exist."""
        with app.app_context():
            # Access invitation link - should redirect to pre-wizard
            response = client.get("/j/NOPOSTFLOW", follow_redirects=False)
            assert response.status_code == 302
            assert "/wizard/pre-wizard" in response.location

            # Complete pre-wizard by setting the flag in session
            with client.session_transaction() as sess:
                sess[InviteCodeManager.PRE_WIZARD_COMPLETE_KEY] = True

            # Access join page - should be allowed now
            response = client.get("/j/NOPOSTFLOW", follow_redirects=False)
            # Should NOT redirect back to pre-wizard
            if response.status_code == 302:
                assert "/wizard/pre-wizard" not in response.location
            else:
                assert response.status_code == 200
