"""
End-to-end tests for invitation workflows using Playwright.

These tests simulate the complete user journey from receiving an invitation
link to successfully creating accounts on media servers.
"""

from unittest.mock import patch

import pytest
from playwright.sync_api import Page, expect

from app.extensions import db
from app.models import Invitation, MediaServer
from tests.mocks.media_server_mocks import (
    create_mock_client,
    get_mock_state,
    setup_mock_servers,
)


@pytest.fixture
def invitation_setup(app):
    """Setup test data for invitation E2E tests."""
    with app.app_context():
        setup_mock_servers()

        # Create media server
        server = MediaServer(
            name="Test Jellyfin Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-api-key",
        )
        db.session.add(server)
        db.session.flush()

        # Create valid invitation
        invitation = Invitation(
            code="E2ETEST123",
            duration="30",
            used=False,
            unlimited=False,
        )
        invitation.servers = [server]
        db.session.add(invitation)
        db.session.commit()

        yield {
            "server": server,
            "invitation": invitation,
            "invitation_url": f"/j/{invitation.code}",
        }


class TestInvitationUserJourney:
    """Test complete user journey through invitation process."""

    @patch("app.services.media.service.get_client_for_media_server")
    def test_successful_invitation_flow(
        self, mock_get_client, page: Page, live_server, invitation_setup
    ):
        """Test successful invitation acceptance and account creation."""
        # Setup mock client
        mock_client = create_mock_client(
            "jellyfin", server_id=invitation_setup["server"].id
        )
        mock_get_client.return_value = mock_client

        # Navigate to invitation page
        page.goto(f"{live_server.url()()}{invitation_setup['invitation_url']}")

        # Verify invitation page loads
        expect(page.locator("h1")).to_contain_text("Join Test Jellyfin Server")

        # Check that form is present
        expect(page.locator("form")).to_be_visible()
        expect(page.locator("input[name='username']")).to_be_visible()
        expect(page.locator("input[name='password']")).to_be_visible()
        expect(page.locator("input[name='confirm']")).to_be_visible()
        expect(page.locator("input[name='email']")).to_be_visible()

        # Fill out the form
        page.fill("input[name='username']", "e2etestuser")
        page.fill("input[name='password']", "testpassword123")
        page.fill("input[name='confirm']", "testpassword123")
        page.fill("input[name='email']", "e2etest@example.com")

        # Submit the form
        page.click("button[type='submit']")

        # Wait for success (should redirect to wizard or success page)
        # Adjust this based on your actual success flow
        page.wait_for_url("**/wizard/**", timeout=10000)

        # Verify success indicators
        expect(page.locator("body")).to_contain_text("success", ignore_case=True)

        # Verify user was created in mock server
        mock_users = get_mock_state().users
        assert len(mock_users) == 1
        created_user = list(mock_users.values())[0]
        assert created_user.username == "e2etestuser"
        assert created_user.email == "e2etest@example.com"

    @patch("app.services.media.service.get_client_for_media_server")
    def test_invitation_form_validation(
        self, mock_get_client, page: Page, live_server, invitation_setup
    ):
        """Test form validation on invitation page."""
        mock_client = create_mock_client(
            "jellyfin", server_id=invitation_setup["server"].id
        )
        mock_get_client.return_value = mock_client

        # Navigate to invitation page
        page.goto(f"{live_server.url()()}{invitation_setup['invitation_url']}")

        # Test empty form submission
        page.click("button[type='submit']")

        # Should show validation errors
        expect(page.locator(".error, .alert-danger, [data-error]")).to_be_visible()

        # Test password mismatch
        page.fill("input[name='username']", "testuser")
        page.fill("input[name='password']", "password123")
        page.fill("input[name='confirm']", "differentpassword")
        page.fill("input[name='email']", "test@example.com")
        page.click("button[type='submit']")

        # Should show password mismatch error
        expect(page.locator("body")).to_contain_text("password", ignore_case=True)
        expect(page.locator("body")).to_contain_text("match", ignore_case=True)

        # Test invalid email
        page.fill("input[name='confirm']", "password123")  # Fix password
        page.fill("input[name='email']", "invalid-email")
        page.click("button[type='submit']")

        # Should show email validation error
        expect(page.locator("body")).to_contain_text("email", ignore_case=True)

    def test_expired_invitation(self, page: Page, live_server, app):
        """Test that expired invitations show appropriate error."""
        with app.app_context():
            from datetime import UTC, datetime, timedelta

            # Create expired invitation
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            expired_invitation = Invitation(
                code="EXPIRED123",
                expires=datetime.now(UTC) - timedelta(hours=1),
                used=False,
            )
            expired_invitation.servers = [server]
            db.session.add(expired_invitation)
            db.session.commit()

        # Navigate to expired invitation
        page.goto(f"{live_server.url()}/j/EXPIRED123")

        # Should show expiry error
        expect(page.locator("body")).to_contain_text("expired", ignore_case=True)

        # Form should not be present
        expect(page.locator("form")).not_to_be_visible()

    def test_invalid_invitation_code(self, page: Page, live_server):
        """Test that invalid invitation codes show 404 or error page."""
        # Navigate to non-existent invitation
        page.goto(f"{live_server.url()}/j/INVALIDCODE123")

        # Should show error (either 404 or invalid invitation message)
        page.wait_for_load_state("networkidle")

        # Check for either 404 or invalid invitation message
        body_text = page.locator("body").inner_text().lower()
        assert any(
            phrase in body_text
            for phrase in ["not found", "invalid", "expired", "does not exist", "404"]
        )

    @patch("app.services.media.service.get_client_for_media_server")
    def test_server_error_handling(
        self, mock_get_client, page: Page, live_server, invitation_setup
    ):
        """Test handling when media server is unavailable."""
        # Setup failing mock client
        mock_client = create_mock_client(
            "jellyfin", server_id=invitation_setup["server"].id
        )
        mock_client._do_join = lambda *args, **kwargs: (
            False,
            "Server temporarily unavailable",
        )
        mock_get_client.return_value = mock_client

        # Navigate to invitation page
        page.goto(f"{live_server.url()()}{invitation_setup['invitation_url']}")

        # Fill and submit form
        page.fill("input[name='username']", "erroruser")
        page.fill("input[name='password']", "testpass123")
        page.fill("input[name='confirm']", "testpass123")
        page.fill("input[name='email']", "error@example.com")
        page.click("button[type='submit']")

        # Should show server error
        expect(page.locator("body")).to_contain_text("server", ignore_case=True)
        expect(page.locator("body")).to_contain_text("unavailable", ignore_case=True)

        # Form should still be visible for retry
        expect(page.locator("form")).to_be_visible()


class TestMultiServerInvitationFlow:
    """Test E2E flows for multi-server invitations."""

    @patch("app.services.media.service.get_client_for_media_server")
    def test_multi_server_invitation_success(
        self, mock_get_client, page: Page, live_server, app
    ):
        """Test successful multi-server invitation flow."""
        with app.app_context():
            setup_mock_servers()

            # Create multiple servers
            jellyfin_server = MediaServer(
                name="Jellyfin Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="jellyfin-key",
            )
            plex_server = MediaServer(
                name="Plex Server",
                server_type="plex",
                url="http://localhost:32400",
                api_key="plex-key",
            )
            db.session.add_all([jellyfin_server, plex_server])
            db.session.flush()

            # Create multi-server invitation
            invitation = Invitation(code="MULTI123", duration="30", used=False)
            invitation.servers = [jellyfin_server, plex_server]
            db.session.add(invitation)
            db.session.commit()

        # Setup mock clients
        def get_client_side_effect(server):
            if server.server_type == "jellyfin":
                return create_mock_client("jellyfin", server_id=server.id)
            if server.server_type == "plex":
                return create_mock_client("plex", server_id=server.id)
            return None

        mock_get_client.side_effect = get_client_side_effect

        # Navigate to invitation page
        page.goto(f"{live_server.url()}/j/MULTI123")

        # Should show multi-server invitation info
        expect(page.locator("body")).to_contain_text("Jellyfin Server")
        expect(page.locator("body")).to_contain_text("Plex Server")

        # Fill and submit form
        page.fill("input[name='username']", "multiuser")
        page.fill("input[name='password']", "testpass123")
        page.fill("input[name='confirm']", "testpass123")
        page.fill("input[name='email']", "multi@example.com")
        page.click("button[type='submit']")

        # Wait for success
        page.wait_for_url("**/wizard/**", timeout=15000)

        # Verify users created on both servers
        mock_users = get_mock_state().users
        assert len(mock_users) == 2  # One user per server

        usernames = [user.username for user in mock_users.values()]
        assert all(username == "multiuser" for username in usernames)

    @patch("app.services.media.service.get_client_for_media_server")
    def test_multi_server_partial_failure(
        self, mock_get_client, page: Page, live_server, app
    ):
        """Test multi-server invitation with partial failures."""
        with app.app_context():
            setup_mock_servers()

            # Create servers
            jellyfin_server = MediaServer(
                name="Working Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="working-key",
            )
            broken_server = MediaServer(
                name="Broken Server",
                server_type="plex",
                url="http://localhost:32400",
                api_key="broken-key",
            )
            db.session.add_all([jellyfin_server, broken_server])
            db.session.flush()

            invitation = Invitation(code="PARTIAL123", used=False)
            invitation.servers = [jellyfin_server, broken_server]
            db.session.add(invitation)
            db.session.commit()

        # Setup clients - one working, one failing
        def get_client_side_effect(server):
            if server.name == "Working Server":
                return create_mock_client("jellyfin", server_id=server.id)
            client = create_mock_client("plex", server_id=server.id)
            client._do_join = lambda *args, **kwargs: (
                False,
                "Server is down for maintenance",
            )
            return client

        mock_get_client.side_effect = get_client_side_effect

        # Navigate and submit
        page.goto(f"{live_server.url()}/j/PARTIAL123")
        page.fill("input[name='username']", "partialuser")
        page.fill("input[name='password']", "testpass123")
        page.fill("input[name='confirm']", "testpass123")
        page.fill("input[name='email']", "partial@example.com")
        page.click("button[type='submit']")

        # Should show partial success message
        page.wait_for_timeout(2000)  # Allow processing

        # Should mention both success and failure
        body_text = page.locator("body").inner_text().lower()

        # Should indicate partial success (at least one server worked)
        # and show error for the failed server
        assert "working server" in body_text or "success" in body_text
        assert "broken server" in body_text or "maintenance" in body_text


class TestInvitationUIComponents:
    """Test UI components and interactions on invitation pages."""

    def test_invitation_page_accessibility(
        self, page: Page, live_server, invitation_setup
    ):
        """Test basic accessibility of invitation form."""
        page.goto(f"{live_server.url()()}{invitation_setup['invitation_url']}")

        # Check for form labels
        expect(
            page.locator("label[for*='username'], input[name='username'][aria-label]")
        ).to_be_visible()
        expect(
            page.locator("label[for*='password'], input[name='password'][aria-label]")
        ).to_be_visible()
        expect(
            page.locator("label[for*='email'], input[name='email'][aria-label]")
        ).to_be_visible()

        # Check form has proper structure
        expect(page.locator("form")).to_have_attribute("method", "post")

        # Test keyboard navigation
        page.keyboard.press("Tab")  # Should focus first input
        focused_element = page.evaluate("document.activeElement.name")
        assert focused_element in ["username", "password", "email"]

    def test_responsive_design(self, page: Page, live_server, invitation_setup):
        """Test invitation page on different screen sizes."""
        # Test desktop
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(f"{live_server.url()()}{invitation_setup['invitation_url']}")
        expect(page.locator("form")).to_be_visible()

        # Test tablet
        page.set_viewport_size({"width": 768, "height": 1024})
        page.reload()
        expect(page.locator("form")).to_be_visible()

        # Test mobile
        page.set_viewport_size({"width": 375, "height": 667})
        page.reload()
        expect(page.locator("form")).to_be_visible()

        # Form should remain usable at all sizes
        expect(page.locator("input[name='username']")).to_be_visible()
        expect(page.locator("button[type='submit']")).to_be_visible()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed"])  # Run with visible browser for debugging
