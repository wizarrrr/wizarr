"""
Unit tests for InviteCodeManager service.

Tests cover:
- Invite code storage and retrieval
- Invite code validation (valid, expired, used)
- Pre-wizard completion flag
- Session cleanup
"""

import datetime
from datetime import timedelta

from app.extensions import db
from app.models import Invitation, MediaServer
from app.services.invite_code_manager import InviteCodeManager


class TestInviteCodeStorage:
    """Test invite code storage and retrieval."""

    def test_store_and_retrieve_invite_code(self, app, client):
        """Test that invite code can be stored and retrieved from session."""
        with app.app_context():
            with client.session_transaction():
                # Store invite code
                InviteCodeManager.store_invite_code("TEST123")

            with client.session_transaction():
                # Retrieve invite code
                code = InviteCodeManager.get_invite_code()
                assert code == "TEST123"

    def test_get_invite_code_when_not_stored(self, app, client):
        """Test that get_invite_code returns None when no code is stored."""
        with app.app_context(), client.session_transaction():
            code = InviteCodeManager.get_invite_code()
            assert code is None

    def test_store_overwrites_previous_code(self, app, client):
        """Test that storing a new code overwrites the previous one."""
        with app.app_context():
            with client.session_transaction():
                InviteCodeManager.store_invite_code("FIRST123")

            with client.session_transaction():
                InviteCodeManager.store_invite_code("SECOND123")

            with client.session_transaction():
                code = InviteCodeManager.get_invite_code()
                assert code == "SECOND123"


class TestInviteCodeValidation:
    """Test invite code validation logic."""

    def test_validate_valid_invitation(self, app, client):
        """Test validation of a valid invitation."""
        with app.app_context():
            # Create a valid invitation
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
                used=False,
                expires=datetime.datetime.now() + timedelta(days=7),
            )
            invitation.servers.append(server)
            db.session.add(invitation)
            db.session.commit()

            # Validate
            is_valid, inv = InviteCodeManager.validate_invite_code("VALID123")
            assert is_valid is True
            assert inv is not None
            assert inv.code == "VALID123"

    def test_validate_case_insensitive(self, app, client):
        """Test that validation is case-insensitive."""
        with app.app_context():
            # Create invitation with uppercase code
            invitation = Invitation(
                code="UPPER123",
                unlimited=True,
                used=False,
            )
            db.session.add(invitation)
            db.session.commit()

            # Validate with lowercase
            is_valid, inv = InviteCodeManager.validate_invite_code("upper123")
            assert is_valid is True
            assert inv is not None
            assert inv.code == "UPPER123"

    def test_validate_expired_invitation(self, app, client):
        """Test that expired invitations are rejected."""
        with app.app_context():
            # Create expired invitation
            invitation = Invitation(
                code="EXPIRED123",
                unlimited=False,
                used=False,
                expires=datetime.datetime.now() - timedelta(hours=1),
            )
            db.session.add(invitation)
            db.session.commit()

            # Validate
            is_valid, inv = InviteCodeManager.validate_invite_code("EXPIRED123")
            assert is_valid is False
            assert inv is None

    def test_validate_used_limited_invitation(self, app, client):
        """Test that used limited invitations are rejected."""
        with app.app_context():
            # Create used limited invitation
            invitation = Invitation(
                code="USED123",
                unlimited=False,
                used=True,
            )
            db.session.add(invitation)
            db.session.commit()

            # Validate
            is_valid, inv = InviteCodeManager.validate_invite_code("USED123")
            assert is_valid is False
            assert inv is None

    def test_validate_used_unlimited_invitation(self, app, client):
        """Test that used unlimited invitations are still valid."""
        with app.app_context():
            # Create used unlimited invitation
            invitation = Invitation(
                code="UNLIMITED123",
                unlimited=True,
                used=True,
            )
            db.session.add(invitation)
            db.session.commit()

            # Validate
            is_valid, inv = InviteCodeManager.validate_invite_code("UNLIMITED123")
            assert is_valid is True
            assert inv is not None

    def test_validate_nonexistent_invitation(self, app, client):
        """Test that nonexistent invitations are rejected."""
        with app.app_context():
            # Validate code that doesn't exist
            is_valid, inv = InviteCodeManager.validate_invite_code("NOTEXIST123")
            assert is_valid is False
            assert inv is None

    def test_validate_empty_code(self, app, client):
        """Test that empty code is rejected."""
        with app.app_context():
            # Validate empty code
            is_valid, inv = InviteCodeManager.validate_invite_code("")
            assert is_valid is False
            assert inv is None

    def test_validate_none_code(self, app, client):
        """Test that None code is rejected."""
        with app.app_context():
            # Validate None code
            is_valid, inv = InviteCodeManager.validate_invite_code(None)
            assert is_valid is False
            assert inv is None


class TestPreWizardCompletion:
    """Test pre-wizard completion flag management."""

    def test_mark_pre_wizard_complete(self, app, client):
        """Test marking pre-wizard as complete."""
        with app.app_context():
            with client.session_transaction():
                # Initially not complete
                assert InviteCodeManager.is_pre_wizard_complete() is False

            with client.session_transaction():
                # Mark as complete
                InviteCodeManager.mark_pre_wizard_complete()

            with client.session_transaction():
                # Check completion status
                assert InviteCodeManager.is_pre_wizard_complete() is True

    def test_is_pre_wizard_complete_default_false(self, app, client):
        """Test that pre-wizard completion defaults to False."""
        with app.app_context(), client.session_transaction():
            assert InviteCodeManager.is_pre_wizard_complete() is False


class TestSessionCleanup:
    """Test session data cleanup."""

    def test_clear_invite_data_removes_code(self, app, client):
        """Test that clear_invite_data removes stored invite code."""
        with app.app_context():
            with client.session_transaction():
                # Store invite code
                InviteCodeManager.store_invite_code("TEST123")

            with client.session_transaction():
                # Clear data
                InviteCodeManager.clear_invite_data()

            with client.session_transaction():
                # Verify code is removed
                code = InviteCodeManager.get_invite_code()
                assert code is None

    def test_clear_invite_data_removes_completion_flag(self, app, client):
        """Test that clear_invite_data removes pre-wizard completion flag."""
        with app.app_context():
            with client.session_transaction():
                # Mark pre-wizard as complete
                InviteCodeManager.mark_pre_wizard_complete()

            with client.session_transaction():
                # Clear data
                InviteCodeManager.clear_invite_data()

            with client.session_transaction():
                # Verify flag is removed
                assert InviteCodeManager.is_pre_wizard_complete() is False

    def test_clear_invite_data_removes_all(self, app, client):
        """Test that clear_invite_data removes all invitation-related data."""
        with app.app_context():
            with client.session_transaction():
                # Store both code and completion flag
                InviteCodeManager.store_invite_code("TEST123")
                InviteCodeManager.mark_pre_wizard_complete()

            with client.session_transaction():
                # Clear all data
                InviteCodeManager.clear_invite_data()

            with client.session_transaction():
                # Verify everything is removed
                assert InviteCodeManager.get_invite_code() is None
                assert InviteCodeManager.is_pre_wizard_complete() is False

    def test_clear_invite_data_when_empty(self, app, client):
        """Test that clear_invite_data works when no data is stored."""
        with app.app_context():
            with client.session_transaction():
                # Clear data when nothing is stored (should not raise error)
                InviteCodeManager.clear_invite_data()

            with client.session_transaction():
                # Verify still empty
                assert InviteCodeManager.get_invite_code() is None
                assert InviteCodeManager.is_pre_wizard_complete() is False
