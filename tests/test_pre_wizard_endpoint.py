"""
Unit tests for pre-wizard endpoint.

Tests verify that the pre-wizard routes are properly registered and handle basic cases.
"""

from app.services.invite_code_manager import InviteCodeManager


class TestPreWizardRouteRegistration:
    """Test that pre-wizard routes are properly registered."""

    def test_pre_wizard_route_exists(self, app):
        """Test that /wizard/pre-wizard route is registered."""
        with app.app_context():
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            assert "/wizard/pre-wizard" in rules
            assert "/wizard/pre-wizard/<int:idx>" in rules

    def test_pre_wizard_redirects_without_invite_code(self, app, client):
        """Test that accessing pre-wizard without invite code redirects to home."""
        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        assert response.location == "/"

    def test_pre_wizard_redirects_with_invalid_invite_code(self, app, client):
        """Test that accessing pre-wizard with invalid code redirects to home."""
        with client.session_transaction():
            InviteCodeManager.store_invite_code("INVALID123")

        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        assert response.location == "/"
