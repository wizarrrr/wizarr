"""Tests for wizard start endpoint redirect logic.

This module tests the backward compatibility redirect logic for the /wizard endpoint.
The start() function should intelligently redirect users based on their context:
- Authenticated users → /post-wizard
- Users with invite code → /pre-wizard
- Others → help page (not the admin login)
"""

import pytest

from app.models import Invitation, MediaServer
from app.services.invite_code_manager import InviteCodeManager


@pytest.fixture
def plex_server(session):
    server = MediaServer(
        name="Test Plex",
        server_type="plex",
        url="http://localhost:32400",
    )
    session.add(server)
    session.commit()
    return server


class TestWizardStartRedirect:
    """Test suite for wizard start endpoint redirect logic."""

    def test_authenticated_user_redirects_to_post_wizard(
        self, admin_client, plex_server
    ):
        response = admin_client.get("/wizard/", follow_redirects=False)

        assert response.status_code == 302
        assert "/wizard/post-wizard" in response.location

    def test_user_with_wizard_access_session_redirects_to_post_wizard(
        self, client, session, plex_server
    ):
        """A user who just accepted an invitation goes to /post-wizard."""
        invitation = Invitation(code="TEST123", unlimited=True)
        invitation.servers = [plex_server]
        session.add(invitation)
        session.commit()

        with client.session_transaction() as sess:
            sess["wizard_access"] = invitation.code

        response = client.get("/wizard/", follow_redirects=False)

        assert response.status_code == 302
        assert "/wizard/post-wizard" in response.location

    @pytest.mark.parametrize(
        ("code", "location", "code_kept"),
        [
            ("TEST123", "/wizard/pre-wizard", True),
            # The route clears an invalid invite code.
            ("UNKNOWN1", "/wizard/help", False),
        ],
        ids=["valid", "invalid"],
    )
    def test_user_with_invite_code(
        self, client, session, plex_server, code, location, code_kept
    ):
        invitation = Invitation(code="TEST123", unlimited=True)
        invitation.servers = [plex_server]
        session.add(invitation)
        session.commit()

        with client.session_transaction() as sess:
            sess[InviteCodeManager.STORAGE_KEY] = code
            sess["invitation_in_progress"] = True

        response = client.get("/wizard/", follow_redirects=False)

        assert response.status_code == 302
        assert response.location == location
        with client.session_transaction() as sess:
            assert (InviteCodeManager.STORAGE_KEY in sess) is code_kept

    def test_user_without_context_redirects_to_help_page(
        self, client, session, plex_server
    ):
        """A user without a login or an invite code sees the help page.

        The user does not see the admin login.
        """
        response = client.get("/wizard/", follow_redirects=False)

        assert response.status_code == 302
        assert response.location == "/wizard/help"
