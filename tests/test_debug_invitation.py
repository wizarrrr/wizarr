"""Debug test to understand invitation validation logic."""

import pytest

from app.extensions import db
from app.models import Invitation
from app.services.invites import is_invite_valid


def test_debug_unlimited_invitation(app):
    """Debug test for unlimited invitation validation."""
    with app.app_context():
        # Create used unlimited invitation
        invite = Invitation(code="UNLIMIT123", used=True, unlimited=True)
        db.session.add(invite)
        db.session.commit()

        # Debug the invitation state
        print(f"Invitation code: {invite.code}")
        print(f"Invitation used: {invite.used}")
        print(f"Invitation unlimited: {invite.unlimited}")
        print(f"Used is True: {invite.used is True}")
        print(f"Unlimited is not True: {invite.unlimited is not True}")
        print(
            f"Both conditions: {invite.used is True and invite.unlimited is not True}"
        )

        # Test validation
        is_valid, message = is_invite_valid(invite.code)
        print(f"Is valid: {is_valid}")
        print(f"Message: {message}")

        # This should be valid for unlimited invitations
        assert is_valid, f"Expected valid but got: {message}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
