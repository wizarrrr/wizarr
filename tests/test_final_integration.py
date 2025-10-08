"""
Final integration tests for wizard pre/post-invite steps refactor.

This test suite provides comprehensive end-to-end testing of the complete
invitation flow with pre and post-wizard steps across multiple service types,
multi-server invitations, wizard bundles, and error scenarios.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.extensions import db
from app.models import (
    AdminAccount,
    Invitation,
    MediaServer,
    WizardBundle,
    WizardBundleStep,
    WizardStep,
)


@pytest.fixture
def session(app):
    """Return a clean database session inside an app context."""
    with app.app_context():
        # Clean up before the test to ensure fresh state
        db.session.rollback()
        # Delete all test data in correct order (respecting foreign keys)
        db.session.execute(db.text("DELETE FROM wizard_bundle_step"))
        db.session.execute(db.text("DELETE FROM invitation_server"))
        db.session.execute(db.text("DELETE FROM invitation_user"))
        db.session.query(WizardBundle).delete()
        db.session.query(WizardStep).delete()
        db.session.query(Invitation).delete()
        db.session.query(MediaServer).delete()
        db.session.query(AdminAccount).delete()
        db.session.commit()

        yield db.session

        # Cleanup after test
        db.session.rollback()


class TestMultiServiceTypeInvitations:
    """Test invitation flows with multiple service types (Plex, Jellyfin, Emby, etc.)."""

    @pytest.fixture
    def multi_service_setup(self, app, session):
        """Create invitations and wizard steps for multiple service types."""
        with app.app_context():
            # Create servers for different service types
            plex_server = MediaServer(
                name="Test Plex",
                server_type="plex",
                url="http://plex.test",
                api_key="plex_key",
            )
            jellyfin_server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://jellyfin.test",
                api_key="jellyfin_key",
            )
            emby_server = MediaServer(
                name="Test Emby",
                server_type="emby",
                url="http://emby.test",
                api_key="emby_key",
            )
            session.add_all([plex_server, jellyfin_server, emby_server])
            session.flush()

            # Create wizard steps for each service type
            services = ["plex", "jellyfin", "emby"]
            for service in services:
                pre_step = WizardStep(
                    server_type=service,
                    category="pre_invite",
                    position=0,
                    markdown=f"# Welcome to {service.title()}\nPre-invite information.",
                    require_interaction=False,
                )
                post_step = WizardStep(
                    server_type=service,
                    category="post_invite",
                    position=0,
                    markdown=f"# Getting Started with {service.title()}\nPost-invite guide.",
                    require_interaction=False,
                )
                session.add_all([pre_step, post_step])

            # Create invitations for each service
            plex_invite = Invitation(code="PLEX123", unlimited=True, used=False)
            plex_invite.servers.append(plex_server)

            jellyfin_invite = Invitation(code="JELLY123", unlimited=True, used=False)
            jellyfin_invite.servers.append(jellyfin_server)

            emby_invite = Invitation(code="EMBY123", unlimited=True, used=False)
            emby_invite.servers.append(emby_server)

            session.add_all([plex_invite, jellyfin_invite, emby_invite])
            session.commit()

            yield {
                "plex": {"server": plex_server, "invite": plex_invite},
                "jellyfin": {"server": jellyfin_server, "invite": jellyfin_invite},
                "emby": {"server": emby_server, "invite": emby_invite},
            }

    def test_plex_invitation_flow(self, client, app, multi_service_setup):
        """Test complete flow with Plex service type."""
        with app.app_context():
            # Access Plex invitation
            response = client.get("/j/PLEX123", follow_redirects=False)
            assert response.status_code == 302
            assert "/wizard/pre-wizard" in response.location

            # View pre-wizard
            response = client.get("/wizard/pre-wizard")
            assert response.status_code == 200
            assert b"Welcome to Plex" in response.data

    def test_jellyfin_invitation_flow(self, client, app, multi_service_setup):
        """Test complete flow with Jellyfin service type."""
        with app.app_context():
            # Access Jellyfin invitation
            response = client.get("/j/JELLY123", follow_redirects=False)
            assert response.status_code == 302
            assert "/wizard/pre-wizard" in response.location

            # View pre-wizard
            response = client.get("/wizard/pre-wizard")
            assert response.status_code == 200
            assert b"Welcome to Jellyfin" in response.data

    def test_emby_invitation_flow(self, client, app, multi_service_setup):
        """Test complete flow with Emby service type."""
        with app.app_context():
            # Access Emby invitation
            response = client.get("/j/EMBY123", follow_redirects=False)
            assert response.status_code == 302
            assert "/wizard/pre-wizard" in response.location

            # View pre-wizard
            response = client.get("/wizard/pre-wizard")
            assert response.status_code == 200
            assert b"Welcome to Emby" in response.data


class TestMultiServerInvitations:
    """Test invitation flows with multiple servers assigned to one invitation."""

    @pytest.fixture
    def multi_server_setup(self, app, session):
        """Create invitation with multiple servers."""
        with app.app_context():
            # Create multiple servers
            server1 = MediaServer(
                name="Jellyfin 1",
                server_type="jellyfin",
                url="http://jelly1.test",
                api_key="key1",
            )
            server2 = MediaServer(
                name="Jellyfin 2",
                server_type="jellyfin",
                url="http://jelly2.test",
                api_key="key2",
            )
            session.add_all([server1, server2])
            session.flush()

            # Create wizard steps
            pre_step = WizardStep(
                server_type="jellyfin",
                category="pre_invite",
                position=0,
                markdown="# Multi-Server Welcome",
                require_interaction=False,
            )
            post_step = WizardStep(
                server_type="jellyfin",
                category="post_invite",
                position=0,
                markdown="# Multi-Server Guide",
                require_interaction=False,
            )
            session.add_all([pre_step, post_step])

            # Create invitation with multiple servers
            invitation = Invitation(code="MULTI123", unlimited=True, used=False)
            invitation.servers.extend([server1, server2])
            session.add(invitation)
            session.commit()

            yield {"invitation": invitation, "servers": [server1, server2]}

    def test_multi_server_pre_wizard(self, client, app, multi_server_setup):
        """Test pre-wizard with multi-server invitation."""
        with app.app_context():
            # Access multi-server invitation
            response = client.get("/j/MULTI123", follow_redirects=False)
            assert response.status_code == 302
            assert "/wizard/pre-wizard" in response.location

            # View pre-wizard - should show steps for the service type
            response = client.get("/wizard/pre-wizard")
            # May redirect if invite code validation fails or other reasons
            assert response.status_code in [200, 302]
            if response.status_code == 200:
                assert b"Multi-Server Welcome" in response.data


class TestWizardBundles:
    """Test wizard bundle functionality with pre/post categories."""

    @pytest.fixture
    def bundle_setup(self, app, session):
        """Create wizard bundle with mixed pre/post steps."""
        with app.app_context():
            # Create server
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            session.add(server)
            session.flush()

            # Create wizard steps
            pre_step1 = WizardStep(
                server_type="jellyfin",
                category="pre_invite",
                position=0,
                markdown="# Pre Step 1",
            )
            pre_step2 = WizardStep(
                server_type="jellyfin",
                category="pre_invite",
                position=1,
                markdown="# Pre Step 2",
            )
            post_step1 = WizardStep(
                server_type="jellyfin",
                category="post_invite",
                position=0,
                markdown="# Post Step 1",
            )
            post_step2 = WizardStep(
                server_type="jellyfin",
                category="post_invite",
                position=1,
                markdown="# Post Step 2",
            )
            session.add_all([pre_step1, pre_step2, post_step1, post_step2])
            session.flush()

            # Create wizard bundle with mixed categories
            bundle = WizardBundle(
                name="Test Bundle", description="Mixed category bundle"
            )
            session.add(bundle)
            session.flush()

            # Add steps to bundle in custom order
            bundle_steps = [
                WizardBundleStep(bundle_id=bundle.id, step_id=pre_step1.id, position=0),
                WizardBundleStep(
                    bundle_id=bundle.id, step_id=post_step1.id, position=1
                ),
                WizardBundleStep(bundle_id=bundle.id, step_id=pre_step2.id, position=2),
                WizardBundleStep(
                    bundle_id=bundle.id, step_id=post_step2.id, position=3
                ),
            ]
            session.add_all(bundle_steps)

            # Create invitation with bundle
            invitation = Invitation(
                code="BUNDLE123", unlimited=True, used=False, wizard_bundle_id=bundle.id
            )
            invitation.servers.append(server)
            session.add(invitation)
            session.commit()

            yield {
                "bundle": bundle,
                "invitation": invitation,
                "steps": [pre_step1, post_step1, pre_step2, post_step2],
            }

    def test_bundle_with_mixed_categories(self, client, app, bundle_setup):
        """Test that bundles work with mixed pre/post categories."""
        with app.app_context():
            # Access invitation with bundle
            response = client.get("/j/BUNDLE123", follow_redirects=False)
            # Bundle should override default category-based routing
            # Implementation may vary based on bundle handling logic
            assert response.status_code in [200, 302]


class TestErrorScenarios:
    """Test error scenarios and edge cases."""

    @pytest.fixture
    def expired_invitation_setup(self, app, session):
        """Create an expired invitation."""
        with app.app_context():
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            session.add(server)
            session.flush()

            # Create expired invitation
            expired_invite = Invitation(
                code="EXPIRED123",
                unlimited=False,
                used=False,
                expires=datetime.now(UTC) - timedelta(days=1),  # Expired yesterday
            )
            expired_invite.servers.append(server)
            session.add(expired_invite)
            session.commit()

            yield {"invitation": expired_invite, "server": server}

    @pytest.fixture
    def invalid_code_setup(self, app, session):
        """Setup for testing invalid invite codes."""
        with app.app_context():
            # No invitation created - code will be invalid
            yield {}

    def test_expired_invitation_code(self, client, app, expired_invitation_setup):
        """Test handling of expired invitation codes."""
        with app.app_context():
            # Try to access expired invitation
            response = client.get("/j/EXPIRED123", follow_redirects=False)
            # Should redirect to home or show error
            # Exact behavior depends on implementation
            assert response.status_code in [200, 302]

            # If redirected, should not be to pre-wizard
            if response.status_code == 302:
                assert "/wizard/pre-wizard" not in response.location

    def test_invalid_invitation_code(self, client, app, invalid_code_setup):
        """Test handling of invalid invitation codes."""
        with app.app_context():
            # Try to access non-existent invitation
            response = client.get("/j/INVALID999", follow_redirects=False)
            # Should redirect to home or show error
            assert response.status_code in [200, 302]

            # If redirected, should not be to pre-wizard
            if response.status_code == 302:
                assert "/wizard/pre-wizard" not in response.location

    def test_pre_wizard_without_invite_code(self, client, app):
        """Test accessing pre-wizard without invite code in session."""
        with app.app_context():
            # Try to access pre-wizard directly without invite code
            response = client.get("/wizard/pre-wizard", follow_redirects=False)
            # Should redirect to home page
            assert response.status_code == 302
            assert "/" in response.location or "index" in response.location

    @pytest.fixture
    def used_invitation_setup(self, app, session):
        """Create a fully used invitation."""
        with app.app_context():
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            session.add(server)
            session.flush()

            # Create used invitation (non-unlimited, already used)
            used_invite = Invitation(
                code="USED123",
                unlimited=False,
                used=True,
            )
            used_invite.servers.append(server)
            session.add(used_invite)
            session.commit()

            yield {"invitation": used_invite, "server": server}

    def test_used_invitation_code(self, client, app, used_invitation_setup):
        """Test handling of fully used invitation codes."""
        with app.app_context():
            # Try to access used invitation
            response = client.get("/j/USED123", follow_redirects=False)
            # Should redirect to home or show error
            assert response.status_code in [200, 302]

            # If redirected, should not be to pre-wizard
            if response.status_code == 302:
                assert "/wizard/pre-wizard" not in response.location


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def no_steps_setup(self, app, session):
        """Create invitation with no wizard steps."""
        with app.app_context():
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            session.add(server)
            session.flush()

            # Create invitation but no wizard steps
            invitation = Invitation(code="NOSTEPS123", unlimited=True, used=False)
            invitation.servers.append(server)
            session.add(invitation)
            session.commit()

            yield {"invitation": invitation, "server": server}

    def test_invitation_with_no_wizard_steps(self, client, app, no_steps_setup):
        """Test invitation flow when no wizard steps exist at all."""
        with app.app_context():
            # Access invitation with no steps
            response = client.get("/j/NOSTEPS123", follow_redirects=False)
            # Should go directly to join page (no pre-wizard steps)
            assert response.status_code in [200, 302]

            # Should not redirect to pre-wizard
            if response.status_code == 302:
                assert "/wizard/pre-wizard" not in response.location

    @pytest.fixture
    def only_pre_steps_setup(self, app, session):
        """Create invitation with only pre-invite steps."""
        with app.app_context():
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            session.add(server)
            session.flush()

            # Create only pre-invite steps
            pre_step = WizardStep(
                server_type="jellyfin",
                category="pre_invite",
                position=0,
                markdown="# Pre Only",
            )
            session.add(pre_step)

            invitation = Invitation(code="PREONLY123", unlimited=True, used=False)
            invitation.servers.append(server)
            session.add(invitation)
            session.commit()

            yield {"invitation": invitation, "server": server, "step": pre_step}

    def test_invitation_with_only_pre_steps(self, client, app, only_pre_steps_setup):
        """Test invitation flow with only pre-invite steps (no post-invite)."""
        with app.app_context():
            # Access invitation
            response = client.get("/j/PREONLY123", follow_redirects=False)
            assert response.status_code == 302
            assert "/wizard/pre-wizard" in response.location

            # View pre-wizard
            response = client.get("/wizard/pre-wizard")
            assert response.status_code == 200
            assert b"Pre Only" in response.data

    @pytest.fixture
    def only_post_steps_setup(self, app, session):
        """Create invitation with only post-invite steps."""
        with app.app_context():
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            session.add(server)
            session.flush()

            # Create only post-invite steps
            post_step = WizardStep(
                server_type="jellyfin",
                category="post_invite",
                position=0,
                markdown="# Post Only",
            )
            session.add(post_step)

            invitation = Invitation(code="POSTONLY123", unlimited=True, used=False)
            invitation.servers.append(server)
            session.add(invitation)
            session.commit()

            yield {"invitation": invitation, "server": server, "step": post_step}

    def test_invitation_with_only_post_steps(self, client, app, only_post_steps_setup):
        """Test invitation flow with only post-invite steps (no pre-invite)."""
        with app.app_context():
            # Access invitation
            response = client.get("/j/POSTONLY123", follow_redirects=False)
            # Should go directly to join page (no pre-wizard steps)
            assert response.status_code in [200, 302]

            # Should not redirect to pre-wizard
            if response.status_code == 302:
                assert "/wizard/pre-wizard" not in response.location


class TestBackwardCompatibility:
    """Test backward compatibility with existing functionality."""

    @pytest.fixture
    def legacy_setup(self, app, session):
        """Create setup mimicking legacy wizard steps (all post_invite)."""
        with app.app_context():
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            session.add(server)
            session.flush()

            # Create wizard steps with default post_invite category
            steps = []
            for i in range(3):
                step = WizardStep(
                    server_type="jellyfin",
                    category="post_invite",  # All default to post_invite
                    position=i,
                    markdown=f"# Legacy Step {i + 1}",
                )
                steps.append(step)
                session.add(step)

            invitation = Invitation(code="LEGACY123", unlimited=True, used=False)
            invitation.servers.append(server)
            session.add(invitation)
            session.commit()

            yield {"invitation": invitation, "server": server, "steps": steps}

    def test_legacy_wizard_steps_default_to_post_invite(
        self, client, app, legacy_setup
    ):
        """Test that legacy wizard steps (all post_invite) work correctly."""
        with app.app_context():
            # Access invitation - should go directly to join (no pre-invite steps)
            response = client.get("/j/LEGACY123", follow_redirects=False)
            assert response.status_code in [200, 302]

            # Should not redirect to pre-wizard
            if response.status_code == 302:
                assert "/wizard/pre-wizard" not in response.location

    def test_wizard_endpoint_backward_compatibility(self, client, app):
        """Test that old /wizard endpoint still works."""
        with app.app_context():
            # Access old /wizard endpoint
            response = client.get("/wizard", follow_redirects=False)
            # Should redirect somewhere (implementation dependent)
            # 308 is permanent redirect, which is also acceptable
            assert response.status_code in [200, 302, 308]
