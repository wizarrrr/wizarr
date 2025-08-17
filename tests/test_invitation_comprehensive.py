"""
Comprehensive invitation system tests with API simulation.

This test suite covers the complete invitation workflow including:
- Single and multi-server invitations
- Various media server types (Jellyfin, Plex, Audiobookshelf)
- Error scenarios and rollback behavior
- Library assignment and user permissions
- Expiry and limitation handling
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from app.extensions import db
from app.models import Invitation, Library, MediaServer, User
from app.services.invitation_manager import InvitationManager
from app.services.invites import create_invite, is_invite_valid, mark_server_used
from tests.mocks.media_server_mocks import (
    create_mock_client,
    get_mock_state,
    setup_mock_servers,
    simulate_server_failure,
    simulate_user_creation_failure,
)


class TestInvitationValidation:
    """Test invitation validation logic."""

    def test_valid_invitation(self, app):
        """Test that valid invitations pass validation."""
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

            # Create invitation using form-like data
            form_data = {
                "duration": "30",
                "expires": "month",
                "unlimited": False,
                "server_ids": [str(server.id)],
            }
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
                code="EXPIRED123",
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
            # Create used unlimited invitation
            invite = Invitation(code="UNLIMIT123", used=True, unlimited=True)
            db.session.add(invite)
            db.session.commit()

            # Test validation
            is_valid, message = is_invite_valid(invite.code)
            assert is_valid
            assert message in ["okay", ""]


class TestSingleServerInvitations:
    """Test invitation processing for single media servers."""

    def setup_method(self):
        """Setup for each test."""
        setup_mock_servers()

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_successful_jellyfin_invitation(self, mock_get_client, app):
        """Test successful invitation process for Jellyfin server."""
        with app.app_context():
            # Create server and invitation first
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            # Setup mock client with correct server ID
            mock_client = create_mock_client("jellyfin", server_id=server.id)
            mock_get_client.return_value = mock_client

            invite = Invitation(
                code="JELLYFIN12",
                duration="30",
                used=False,
                unlimited=False,
            )
            invite.servers = [server]
            db.session.add(invite)
            db.session.commit()

            # Process invitation
            success, redirect_code, errors = InvitationManager.process_invitation(
                code="JELLYFIN12",
                username="testuser",
                password="testpass123",
                confirm_password="testpass123",
                email="test@example.com",
            )

            # Verify results
            assert success
            assert redirect_code == "JELLYFIN12"
            assert len(errors) == 0

            # Verify user was created in mock
            mock_users = get_mock_state().users
            assert len(mock_users) == 1
            created_user = list(mock_users.values())[0]
            assert created_user.username == "testuser"
            assert created_user.email == "test@example.com"

            # Verify database user was created
            db_user = User.query.filter_by(code="JELLYFIN12").first()
            assert db_user is not None
            assert db_user.username == "testuser"
            assert db_user.server_id == server.id

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_plex_invitation_with_oauth(self, mock_get_client, app):
        """Test Plex invitation that might use OAuth flow."""
        with app.app_context():
            # Create Plex server
            server = MediaServer(
                name="Test Plex",
                server_type="plex",
                url="http://localhost:32400",
                api_key="plex-token",
            )
            db.session.add(server)
            db.session.flush()

            mock_client = create_mock_client("plex", server_id=server.id)
            mock_get_client.return_value = mock_client

            invite = Invitation(
                code="PLEX123",
                plex_home=True,
                plex_allow_sync=True,
                unlimited=True,
            )
            invite.servers = [server]
            db.session.add(invite)
            db.session.commit()

            # Process invitation
            success, redirect_code, errors = InvitationManager.process_invitation(
                code="PLEX123",
                username="plexuser",
                password="plexpass123",
                confirm_password="plexpass123",
                email="plex@example.com",
            )

            assert success
            assert redirect_code == "PLEX123"

            # Verify Plex-specific behavior
            mock_users = get_mock_state().users
            assert len(mock_users) == 1
            created_user = list(mock_users.values())[0]
            assert (
                created_user.email == "plex@example.com"
            )  # Plex uses email as primary identifier

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_server_connection_failure(self, mock_get_client, app):
        """Test handling of server connection failures."""
        with app.app_context():
            # Create server and invitation
            server = MediaServer(
                name="Failing Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            # Simulate connection failure
            simulate_server_failure()

            mock_client = create_mock_client("jellyfin", server_id=server.id)
            mock_get_client.return_value = mock_client

            invite = Invitation(code="FAIL123")
            invite.servers = [server]
            db.session.add(invite)
            db.session.commit()

            # Process invitation
            success, redirect_code, errors = InvitationManager.process_invitation(
                code="FAIL123",
                username="testuser",
                password="testpass123",
                confirm_password="testpass123",
                email="test@example.com",
            )

            # Should fail due to connection issue
            assert not success
            assert redirect_code is None
            assert len(errors) > 0
            assert any(
                "Connection failed" in error or "server unreachable" in error.lower()
                for error in errors
            )

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_user_creation_failure(self, mock_get_client, app):
        """Test handling when user creation fails on media server."""
        with app.app_context():
            # Create server and invitation
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            # Simulate user creation failure
            simulate_user_creation_failure(["baduser"])

            mock_client = create_mock_client("jellyfin", server_id=server.id)
            mock_get_client.return_value = mock_client

            invite = Invitation(code="BADUSER123")
            invite.servers = [server]
            db.session.add(invite)
            db.session.commit()

            # Process invitation with username that will fail
            success, redirect_code, errors = InvitationManager.process_invitation(
                code="BADUSER123",
                username="baduser",
                password="testpass123",
                confirm_password="testpass123",
                email="test@example.com",
            )

            # Should fail due to user creation issue
            assert not success
            assert redirect_code is None
            assert len(errors) > 0
            assert any("Failed to create user baduser" in error for error in errors)


class TestMultiServerInvitations:
    """Test invitation processing across multiple media servers."""

    def setup_method(self):
        """Setup for each test."""
        setup_mock_servers()

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_multi_server_success(self, mock_get_client, app):
        """Test successful multi-server invitation."""
        with app.app_context():
            # Setup multiple servers
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
            invite = Invitation(code="MULTI123", duration="30", unlimited=False)
            invite.servers = [jellyfin_server, plex_server]
            db.session.add(invite)
            db.session.commit()

            # Setup mock clients
            def get_client_side_effect(server):
                if server.server_type == "jellyfin":
                    return create_mock_client("jellyfin", server_id=server.id)
                if server.server_type == "plex":
                    return create_mock_client("plex", server_id=server.id)
                return None

            mock_get_client.side_effect = get_client_side_effect

            # Process invitation
            success, redirect_code, errors = InvitationManager.process_invitation(
                code="MULTI123",
                username="multiuser",
                password="testpass123",
                confirm_password="testpass123",
                email="multi@example.com",
            )

            # Should succeed on both servers
            assert success
            assert redirect_code == "MULTI123"
            assert len(errors) == 0  # No errors expected

            # Verify users created on both servers
            mock_users = get_mock_state().users
            assert len(mock_users) == 2  # One user per server

            # Verify database users
            db_users = User.query.filter_by(code="MULTI123").all()
            assert len(db_users) == 2
            server_ids = {user.server_id for user in db_users}
            assert server_ids == {jellyfin_server.id, plex_server.id}

            # Verify identity linking (users should share same identity)
            identities = {user.identity_id for user in db_users if user.identity_id}
            assert (
                len(identities) <= 1
            )  # Should be linked to same identity or both None

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_multi_server_partial_failure(self, mock_get_client, app):
        """Test multi-server invitation where one server fails."""
        with app.app_context():
            # Setup servers
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

            # Create invitation
            invite = Invitation(code="PARTIAL123", unlimited=False)
            invite.servers = [jellyfin_server, plex_server]
            db.session.add(invite)
            db.session.commit()

            # Setup clients - make Plex fail
            def get_client_side_effect(server):
                if server.server_type == "jellyfin":
                    return create_mock_client("jellyfin", server_id=server.id)
                if server.server_type == "plex":
                    # Simulate Plex failure
                    client = create_mock_client("plex", server_id=server.id)
                    client._do_join = Mock(return_value=(False, "Plex server error"))
                    return client
                return None

            mock_get_client.side_effect = get_client_side_effect

            # Process invitation
            success, redirect_code, errors = InvitationManager.process_invitation(
                code="PARTIAL123",
                username="partialuser",
                password="testpass123",
                confirm_password="testpass123",
                email="partial@example.com",
            )

            # Should succeed overall (at least one server worked)
            assert success
            assert redirect_code == "PARTIAL123"
            assert len(errors) == 1  # One error from Plex
            assert "Plex server error" in errors[0]

            # Verify only Jellyfin user was created
            mock_users = get_mock_state().users
            jellyfin_users = [
                u for u in mock_users.values() if "Plex server error" not in str(u)
            ]
            assert len(jellyfin_users) == 1

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_multi_server_complete_failure(self, mock_get_client, app):
        """Test multi-server invitation where all servers fail."""
        with app.app_context():
            # Setup servers
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
            invite = Invitation(code="ALLFAIL123", unlimited=False)
            invite.servers = [server1, server2]
            db.session.add(invite)
            db.session.commit()

            # Make all servers fail
            def failing_client(server):
                client = create_mock_client("jellyfin", server_id=server.id)
                client._do_join = Mock(return_value=(False, f"{server.name} failed"))
                return client

            mock_get_client.side_effect = failing_client

            # Process invitation
            success, redirect_code, errors = InvitationManager.process_invitation(
                code="ALLFAIL123",
                username="failuser",
                password="testpass123",
                confirm_password="testpass123",
                email="fail@example.com",
            )

            # Should fail completely
            assert not success
            assert redirect_code is None
            assert len(errors) == 2  # Errors from both servers
            assert all("failed" in error for error in errors)


class TestInvitationLibraryAssignment:
    """Test library assignment during invitation processing."""

    def setup_method(self):
        """Setup for each test."""
        setup_mock_servers()

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_specific_library_assignment(self, mock_get_client, app):
        """Test invitation with specific library restrictions."""
        with app.app_context():
            # Setup server
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
            lib3 = Library(
                name="Music", external_id="lib3", server_id=server.id, enabled=True
            )
            db.session.add_all([lib1, lib2, lib3])
            db.session.flush()

            # Create invitation with specific libraries
            invite = Invitation(code="SPECIFIC12")
            invite.servers = [server]
            invite.libraries = [lib1, lib2]  # Only Movies and TV
            db.session.add(invite)
            db.session.commit()

            # Setup mock client
            mock_client = create_mock_client("jellyfin", server_id=server.id)
            mock_get_client.return_value = mock_client

            # Process invitation
            success, redirect_code, errors = InvitationManager.process_invitation(
                code="SPECIFIC12",
                username="libuser",
                password="testpass123",
                confirm_password="testpass123",
                email="lib@example.com",
            )

            assert success

            # Verify user was assigned only specific libraries
            mock_users = get_mock_state().users
            assert len(mock_users) == 1
            created_user = list(mock_users.values())[0]

            # Should have access to lib1 and lib2, but not lib3
            expected_libs = ["lib1", "lib2"]
            assert set(created_user.libraries) == set(expected_libs)


class TestInvitationExpiry:
    """Test invitation expiry and duration handling."""

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_user_expiry_calculation(self, mock_get_client, app):
        """Test that users get proper expiry dates based on invitation duration."""
        with app.app_context():
            # Setup server
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            # Create invitation with 7-day duration
            invite = Invitation(
                code="EXPIRY123",
                duration="7",  # 7 days
            )
            invite.servers = [server]
            db.session.add(invite)
            db.session.commit()

            mock_client = create_mock_client("jellyfin", server_id=server.id)
            mock_get_client.return_value = mock_client

            # Process invitation
            success, redirect_code, errors = InvitationManager.process_invitation(
                code="EXPIRY123",
                username="expiryuser",
                password="testpass123",
                confirm_password="testpass123",
                email="expiry@example.com",
            )

            assert success

            # Verify user has expiry date set
            db_user = User.query.filter_by(code="EXPIRY123").first()
            assert db_user is not None
            assert db_user.expires is not None

            # Should expire in approximately 7 days
            expected_expiry = datetime.now() + timedelta(
                days=7
            )  # Use naive datetime like the database
            time_diff = abs((db_user.expires - expected_expiry).total_seconds())
            assert time_diff < 60  # Within 1 minute of expected


class TestInvitationMarkingUsed:
    """Test invitation usage tracking and server marking."""

    def test_mark_server_used_single_server(self, app):
        """Test marking invitation as used for single server."""
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

            # Create invitation properly with servers relationship
            form_data = {
                "expires": "month",
                "unlimited": False,
                "server_ids": [str(server.id)],
            }
            invite = create_invite(form_data)
            invite.code = "MARK123"  # Set specific code for test

            user = User(
                username="testuser",
                email="test@example.com",
                token="user-token",
                code="MARK123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Mark server as used
            mark_server_used(invite, server.id, user)

            # Verify invitation is marked as used (since only one server and it's limited)
            db.session.refresh(invite)
            assert invite.used is True
            assert invite.used_by == user

            # Verify user is in invitation's users collection
            assert user in invite.users

    def test_mark_server_used_multi_server_partial(self, app):
        """Test marking one server as used in multi-server invitation."""
        with app.app_context():
            # Create multiple servers
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

            # Create invitation for both servers
            invite = Invitation(code="MULTIMARK123", used=False, unlimited=False)
            invite.servers = [server1, server2]
            db.session.add(invite)
            db.session.flush()

            # Create user for first server
            user1 = User(
                username="user1",
                email="user1@example.com",
                token="token1",
                code="MULTIMARK123",
                server_id=server1.id,
            )
            db.session.add(user1)
            db.session.commit()

            # Mark only first server as used
            mark_server_used(invite, server1.id, user1)
            db.session.commit()

            # Invitation should not be fully used yet (limited invitation with multiple servers)
            db.session.refresh(invite)
            assert invite.used is False  # Not all servers used yet

            # But user should be tracked
            assert user1 in invite.users


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
