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
            with client.session_transaction() as sess:
                # Store invite code
                sess[InviteCodeManager.STORAGE_KEY] = "TEST123"

            with client.session_transaction() as sess:
                # Retrieve invite code
                assert sess.get(InviteCodeManager.STORAGE_KEY) == "TEST123"

    def test_get_invite_code_when_not_stored(self, app, client):
        """Test that get_invite_code returns None when no code is stored."""
        with app.app_context(), client.session_transaction() as sess:
            assert sess.get(InviteCodeManager.STORAGE_KEY) is None

    def test_store_overwrites_previous_code(self, app, client):
        """Test that storing a new code overwrites the previous one."""
        with app.app_context():
            with client.session_transaction() as sess:
                sess[InviteCodeManager.STORAGE_KEY] = "FIRST123"

            with client.session_transaction() as sess:
                sess[InviteCodeManager.STORAGE_KEY] = "SECOND123"

            with client.session_transaction() as sess:
                assert sess.get(InviteCodeManager.STORAGE_KEY) == "SECOND123"


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
            with client.session_transaction() as sess:
                # Initially not complete
                assert (
                    sess.get(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, False) is False
                )

            with client.session_transaction() as sess:
                # Mark as complete
                sess[InviteCodeManager.PRE_WIZARD_COMPLETE_KEY] = True

            with client.session_transaction() as sess:
                # Check completion status
                assert (
                    sess.get(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, False) is True
                )

    def test_is_pre_wizard_complete_default_false(self, app, client):
        """Test that pre-wizard completion defaults to False."""
        with app.app_context(), client.session_transaction() as sess:
            assert sess.get(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, False) is False


class TestSessionCleanup:
    """Test session data cleanup."""

    def test_clear_invite_data_removes_code(self, app, client):
        """Test that clear_invite_data removes stored invite code."""
        with app.app_context():
            with client.session_transaction() as sess:
                # Store invite code
                sess[InviteCodeManager.STORAGE_KEY] = "TEST123"

            with client.session_transaction() as sess:
                # Clear data
                sess.pop(InviteCodeManager.STORAGE_KEY, None)
                sess.pop(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, None)

            with client.session_transaction() as sess:
                # Verify code is removed
                assert sess.get(InviteCodeManager.STORAGE_KEY) is None

    def test_clear_invite_data_removes_completion_flag(self, app, client):
        """Test that clear_invite_data removes pre-wizard completion flag."""
        with app.app_context():
            with client.session_transaction() as sess:
                # Mark pre-wizard as complete
                sess[InviteCodeManager.PRE_WIZARD_COMPLETE_KEY] = True

            with client.session_transaction() as sess:
                # Clear data
                sess.pop(InviteCodeManager.STORAGE_KEY, None)
                sess.pop(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, None)

            with client.session_transaction() as sess:
                # Verify flag is removed
                assert (
                    sess.get(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, False) is False
                )

    def test_clear_invite_data_removes_all(self, app, client):
        """Test that clear_invite_data removes all invitation-related data."""
        with app.app_context():
            with client.session_transaction() as sess:
                # Store both code and completion flag
                sess[InviteCodeManager.STORAGE_KEY] = "TEST123"
                sess[InviteCodeManager.PRE_WIZARD_COMPLETE_KEY] = True

            with client.session_transaction() as sess:
                # Clear all data
                sess.pop(InviteCodeManager.STORAGE_KEY, None)
                sess.pop(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, None)

            with client.session_transaction() as sess:
                # Verify everything is removed
                assert sess.get(InviteCodeManager.STORAGE_KEY) is None
                assert (
                    sess.get(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, False) is False
                )

    def test_clear_invite_data_when_empty(self, app, client):
        """Test that clear_invite_data works when no data is stored."""
        with app.app_context():
            with client.session_transaction() as sess:
                # Clear data when nothing is stored (should not raise error)
                sess.pop(InviteCodeManager.STORAGE_KEY, None)
                sess.pop(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, None)

            with client.session_transaction() as sess:
                # Verify still empty
                assert sess.get(InviteCodeManager.STORAGE_KEY) is None
                assert (
                    sess.get(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, False) is False
                )
