"""
Unit tests for invitation system core functionality.

These tests focus on isolated testing of individual components
without complex mocking or external dependencies.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.extensions import db
from app.models import Invitation, Library, MediaServer, User
from app.services.invites import create_invite, is_invite_valid, mark_server_used


class DictFormWrapper:
    """Wrapper to make dict behave like a WTForm for testing."""

    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        return self.data.get(key, default)

    def getlist(self, key):
        value = self.data.get(key, [])
        if isinstance(value, list):
            return value
        return [value] if value is not None else []


class TestInvitationValidation:
    """Test invitation validation logic."""

    def test_valid_invitation_basic(self, app):
        """Test basic invitation validation."""
        with app.app_context():
            # Create server first
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            # Create invitation using form-like data
            form_data = DictFormWrapper(
                {"expires": "month", "unlimited": False, "server_ids": [str(server.id)]}
            )
            invite = create_invite(form_data)

            # Test validation
            is_valid, message = is_invite_valid(invite.code)
            assert is_valid
            assert message == "okay"

    def test_expired_invitation(self, app):
        """Test that expired invitations are rejected."""
        with app.app_context():
            # Create invitation that expires immediately
            invite = Invitation(
                code="EXPIRED12",  # 9 chars, within limit
                expires=datetime.now(UTC) - timedelta(hours=1),
                used=False,
                unlimited=False,
            )
            db.session.add(invite)
            db.session.commit()

            # Test validation
            is_valid, message = is_invite_valid(invite.code)
            assert not is_valid
            assert "expired" in message.lower()

    def test_used_limited_invitation(self, app):
        """Test that used limited invitations are rejected."""
        with app.app_context():
            # Create used limited invitation
            invite = Invitation(code="USED123", used=True, unlimited=False)
            db.session.add(invite)
            db.session.commit()

            # Test validation
            is_valid, message = is_invite_valid(invite.code)
            assert not is_valid
            assert "already been used" in message

    def test_used_unlimited_invitation(self, app):
        """Test that used unlimited invitations are still valid."""
        with app.app_context():
            # Create used unlimited invitation (code must be 6-10 chars)
            invite = Invitation(
                code="UNLIMIT123",  # 10 chars, within limit
                used=True,
                unlimited=True,
            )
            db.session.add(invite)
            db.session.commit()

            # Test validation
            is_valid, message = is_invite_valid(invite.code)
            assert is_valid
            assert message == "okay"

    def test_invalid_code_length(self, app):
        """Test that codes with invalid length are rejected."""
        with app.app_context():
            # Test too short
            is_valid, message = is_invite_valid("AB")
            assert not is_valid
            assert "Invalid code length" in message

            # Test too long
            is_valid, message = is_invite_valid("A" * 50)
            assert not is_valid
            assert "Invalid code length" in message

    def test_nonexistent_code(self, app):
        """Test that non-existent codes are rejected."""
        with app.app_context():
            is_valid, message = is_invite_valid(
                "NOTEXIST12"
            )  # 10 chars, valid length but nonexistent
            assert not is_valid
            assert "Invalid code" in message


class TestInvitationCreation:
    """Test invitation creation functionality."""

    def test_create_basic_invitation(self, app):
        """Test creating a basic invitation."""
        with app.app_context():
            # Create server
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            # Create invitation
            form_data = DictFormWrapper(
                {
                    "expires": "week",
                    "unlimited": True,
                    "server_ids": [str(server.id)],
                    "duration": "14",
                }
            )
            invite = create_invite(form_data)

            # Verify invitation properties
            assert invite.code is not None
            assert len(invite.code) >= 3  # Minimum code size
            assert invite.unlimited is True
            assert invite.duration == "14"
            assert invite.expires is not None
            assert len(invite.servers) == 1
            assert invite.servers[0] == server

    def test_create_invitation_with_libraries(self, app):
        """Test creating invitation with specific libraries."""
        with app.app_context():
            # Create server
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            # Create libraries
            lib1 = Library(
                name="Movies", external_id="lib1", server_id=server.id, enabled=True
            )
            lib2 = Library(
                name="TV Shows", external_id="lib2", server_id=server.id, enabled=True
            )
            db.session.add_all([lib1, lib2])
            db.session.flush()

            # Create invitation with specific libraries
            form_data = DictFormWrapper(
                {
                    "expires": "month",
                    "unlimited": False,
                    "server_ids": [str(server.id)],
                    "libraries": [str(lib1.id), str(lib2.id)],
                }
            )
            invite = create_invite(form_data)

            # Verify library associations
            assert len(invite.libraries) == 2
            library_ids = {lib.id for lib in invite.libraries}
            assert library_ids == {lib1.id, lib2.id}

    def test_create_multi_server_invitation(self, app):
        """Test creating invitation for multiple servers."""
        with app.app_context():
            # Create multiple servers
            server1 = MediaServer(
                name="Jellyfin Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="jellyfin-key",
            )
            server2 = MediaServer(
                name="Plex Server",
                server_type="plex",
                url="http://localhost:32400",
                api_key="plex-key",
            )
            db.session.add_all([server1, server2])
            db.session.flush()

            # Create multi-server invitation
            form_data = DictFormWrapper(
                {
                    "expires": "never",
                    "unlimited": False,
                    "server_ids": [str(server1.id), str(server2.id)],
                }
            )
            invite = create_invite(form_data)

            # Verify server associations
            assert len(invite.servers) == 2
            server_ids = {server.id for server in invite.servers}
            assert server_ids == {server1.id, server2.id}

    def test_create_invitation_validation_errors(self, app):
        """Test invitation creation validation."""
        with app.app_context():
            # Test missing servers
            form_data = DictFormWrapper(
                {
                    "expires": "month",
                    "unlimited": False,
                    "server_ids": [],  # No servers
                }
            )

            with pytest.raises(
                ValueError, match="At least one server must be selected"
            ):
                create_invite(form_data)

    def test_create_invitation_with_custom_code(self, app):
        """Test creating invitation with custom code."""
        with app.app_context():
            # Create server
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            # Create invitation with custom code
            form_data = DictFormWrapper(
                {
                    "code": "CUSTOM123",
                    "expires": "month",
                    "unlimited": False,
                    "server_ids": [str(server.id)],
                }
            )
            invite = create_invite(form_data)

            # Verify custom code
            assert invite.code == "CUSTOM123"


class TestInvitationMarkingUsed:
    """Test invitation usage tracking."""

    def test_mark_unlimited_invitation_used(self, app):
        """Test marking unlimited invitation as used."""
        with app.app_context():
            # Create server
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            # Create unlimited invitation
            form_data = DictFormWrapper(
                {"expires": "month", "unlimited": True, "server_ids": [str(server.id)]}
            )
            invite = create_invite(form_data)

            # Create user
            user = User(
                username="testuser",
                email="test@example.com",
                token="user-token",
                code=invite.code,
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Verify invitation is not marked as used initially
            assert invite.used is False

            # Mark server as used
            mark_server_used(invite, server.id, user)

            # Verify unlimited invitation is marked as used for admin interface
            db.session.refresh(invite)
            assert (
                invite.used is True
            )  # Unlimited invitations get marked used for admin interface
            assert invite.used_by == user

            # But should still be valid for future use
            is_valid, message = is_invite_valid(invite.code)
            assert is_valid

    def test_mark_limited_single_server_used(self, app):
        """Test marking limited single-server invitation as used."""
        with app.app_context():
            # Create server
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            # Create limited invitation
            form_data = DictFormWrapper(
                {"expires": "month", "unlimited": False, "server_ids": [str(server.id)]}
            )
            invite = create_invite(form_data)

            # Create user
            user = User(
                username="testuser",
                email="test@example.com",
                token="user-token",
                code=invite.code,
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Mark server as used
            mark_server_used(invite, server.id, user)

            # Verify limited invitation is fully used (all servers used)
            db.session.refresh(invite)
            assert invite.used is True
            assert invite.used_by == user

            # Should no longer be valid
            is_valid, message = is_invite_valid(invite.code)
            assert not is_valid
            assert "already been used" in message


class TestInvitationRelationships:
    """Test invitation model relationships."""

    def test_invitation_user_relationship(self, app):
        """Test invitation-user many-to-many relationship."""
        with app.app_context():
            # Create invitation
            invite = Invitation(code="RELATION123", used=False, unlimited=True)
            db.session.add(invite)
            db.session.flush()

            # Create users
            user1 = User(
                username="user1",
                email="user1@example.com",
                token="token1",
                code="RELATION123",
                server_id=1,
            )
            user2 = User(
                username="user2",
                email="user2@example.com",
                token="token2",
                code="RELATION123",
                server_id=2,
            )
            db.session.add_all([user1, user2])
            db.session.commit()

            # Test helper methods
            assert invite.get_user_count() == 0  # Not added to relationship yet

            # Add users to invitation
            invite.users.append(user1)
            invite.users.append(user2)
            db.session.commit()

            # Test relationship methods
            assert invite.get_user_count() == 2
            assert invite.has_user(user1)
            assert invite.has_user(user2)

            all_users = invite.get_all_users()
            assert len(all_users) == 2
            assert user1 in all_users
            assert user2 in all_users

            first_user = invite.get_first_user()
            assert first_user in [user1, user2]

    def test_invitation_server_relationship(self, app):
        """Test invitation-server many-to-many relationship."""
        with app.app_context():
            # Create servers
            server1 = MediaServer(
                name="Server 1",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="key1",
            )
            server2 = MediaServer(
                name="Server 2",
                server_type="plex",
                url="http://localhost:32400",
                api_key="key2",
            )
            db.session.add_all([server1, server2])
            db.session.flush()

            # Create invitation
            form_data = DictFormWrapper(
                {
                    "expires": "month",
                    "unlimited": False,
                    "server_ids": [str(server1.id), str(server2.id)],
                }
            )
            invite = create_invite(form_data)

            # Verify server relationships
            assert len(invite.servers) == 2
            assert server1 in invite.servers
            assert server2 in invite.servers

            # Verify reverse relationship
            assert invite in server1.invites
            assert invite in server2.invites


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
