"""
Test cases for the identity linking fix in unlimited invitations.

This test suite verifies that:
1. Unlimited invites do not automatically link users with the same code
2. Limited invites still correctly link users across servers (multi-server case)
3. Email-based linking continues to work as expected
4. Edge cases are handled properly
"""

from app.extensions import db
from app.models import Identity, MediaServer
from app.services.invites import create_invite
from app.services.media.client_base import MediaClient


class MockMediaClient(MediaClient):
    """Mock media client for testing identity linking behavior."""

    def __init__(self, media_server=None):
        super().__init__(media_server=media_server)

    def libraries(self):
        return {"Library 1": "1", "Library 2": "2"}

    def create_user(self, *args, **kwargs):
        return {"success": True, "user_id": "test_user"}

    def update_user(self, *args, **kwargs):
        return {"success": True}

    def delete_user(self, *args, **kwargs):
        return {"success": True}

    def get_user(self, *args, **kwargs):
        return {"username": "test_user", "email": "test@example.com"}

    def list_users(self, *args, **kwargs):
        return []

    def now_playing(self):
        return []

    def statistics(self):
        return {}

    def _do_join(self, username, password, confirm, email, code):
        return True, "User created successfully"

    def scan_libraries(self, url=None, token=None):
        return {"Library 1": "1", "Library 2": "2"}


class TestIdentityLinkingFix:
    """Test the identity linking fix for unlimited vs limited invitations."""

    def setup_method(self):
        """Set up test data for each test method."""
        # Create test servers
        self.server1 = MediaServer(
            name="Jellyfin Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key-1",
        )
        self.server2 = MediaServer(
            name="Plex Server",
            server_type="plex",
            url="http://localhost:32400",
            api_key="test-key-2",
        )
        db.session.add_all([self.server1, self.server2])
        db.session.flush()

    def test_unlimited_invite_different_users_remain_separate(self, app):
        """Test that DIFFERENT users using the same unlimited invite code remain separate identities."""
        with app.app_context():
            self.setup_method()

            # Create unlimited invitation
            form_data = {
                "server_ids": [str(self.server1.id)],
                "unlimited": True,
                "expires": "never",
            }
            invitation = create_invite(form_data)

            # Create mock client
            mock_client = MockMediaClient(media_server=self.server1)

            # Create first user using the unlimited invite
            user1_kwargs = {
                "username": "user1",
                "email": "user1@example.com",
                "code": invitation.code,
                "server_id": self.server1.id,
                "token": "token1",
            }
            user1 = mock_client._create_user_with_identity_linking(user1_kwargs)
            db.session.commit()

            # Create second user using the same unlimited invite code
            user2_kwargs = {
                "username": "user2",
                "email": "user2@example.com",
                "code": invitation.code,
                "server_id": self.server1.id,
                "token": "token2",
            }
            user2 = mock_client._create_user_with_identity_linking(user2_kwargs)
            db.session.commit()

            # Verify users are separate (no shared identity)
            # Both should be None (no identity linking for unlimited invites)
            assert user1.identity_id is None  # First user has no identity_id
            assert user2.identity_id is None  # Second user also has no identity_id
            assert (
                user1.identity_id == user2.identity_id
            )  # Both None means they're not linked

            # Verify they have different usernames and emails
            assert user1.username == "user1"
            assert user2.username == "user2"
            assert user1.email == "user1@example.com"
            assert user2.email == "user2@example.com"

            # Verify they both use the same invitation code but are separate users
            assert user1.code == invitation.code
            assert user2.code == invitation.code
            assert user1.id != user2.id

    def test_limited_invite_users_get_linked_across_servers(self, app):
        """Test that users using the same limited invite across servers get linked."""
        with app.app_context():
            self.setup_method()

            # Create limited (non-unlimited) multi-server invitation
            form_data = {
                "server_ids": [str(self.server1.id), str(self.server2.id)],
                "unlimited": False,
                "expires": "never",
            }
            invitation = create_invite(form_data)

            # Create mock clients for both servers
            mock_client1 = MockMediaClient(media_server=self.server1)
            mock_client2 = MockMediaClient(media_server=self.server2)

            # Create first user on server 1
            user1_kwargs = {
                "username": "john_doe",
                "email": "john@example.com",
                "code": invitation.code,
                "server_id": self.server1.id,
                "token": "token1",
            }
            user1 = mock_client1._create_user_with_identity_linking(user1_kwargs)

            # Create an identity for the first user (simulating what would happen in practice)
            identity = Identity(
                primary_email="john@example.com", primary_username="john_doe"
            )
            db.session.add(identity)
            db.session.flush()
            user1.identity_id = identity.id
            db.session.commit()

            # Create second user on server 2 using the same limited invite
            user2_kwargs = {
                "username": "john_doe_plex",
                "email": "john@example.com",
                "code": invitation.code,
                "server_id": self.server2.id,
                "token": "token2",
            }
            user2 = mock_client2._create_user_with_identity_linking(user2_kwargs)
            db.session.commit()

            # Verify users are linked (shared identity) for limited invitations
            assert user1.identity_id == user2.identity_id
            assert user1.identity_id is not None
            assert user2.identity_id is not None

            # Verify they represent the same person across different servers
            assert user1.code == user2.code == invitation.code
            assert user1.server_id != user2.server_id  # Different servers
            assert user1.email == user2.email  # Same person

    def test_unlimited_invite_with_same_email_remains_separate(self, app):
        """Test that even with same email, unlimited invite users remain separate."""
        with app.app_context():
            self.setup_method()

            # Create unlimited invitation
            form_data = {
                "server_ids": [str(self.server1.id)],
                "unlimited": True,
                "expires": "never",
            }
            invitation = create_invite(form_data)

            mock_client = MockMediaClient(media_server=self.server1)

            # Create first user
            user1_kwargs = {
                "username": "user1",
                "email": "shared@example.com",  # Same email
                "code": invitation.code,
                "server_id": self.server1.id,
                "token": "token1",
            }
            user1 = mock_client._create_user_with_identity_linking(user1_kwargs)
            db.session.commit()

            # Create second user with same email
            user2_kwargs = {
                "username": "user2",
                "email": "shared@example.com",  # Same email
                "code": invitation.code,
                "server_id": self.server1.id,
                "token": "token2",
            }
            user2 = mock_client._create_user_with_identity_linking(user2_kwargs)
            db.session.commit()

            # Verify users remain separate despite same email (no identity linking via code)
            # Both should be None (no identity linking for unlimited invites)
            assert user1.identity_id is None
            assert user2.identity_id is None
            assert (
                user1.identity_id == user2.identity_id
            )  # Both None means they're not linked

            # They will be grouped in UI by email via _group_users_for_display(),
            # but they don't share an actual identity_id in the database
            assert user1.email == user2.email == "shared@example.com"
            assert user1.id != user2.id

    def test_mixed_scenario_unlimited_then_limited(self, app):
        """Test mixed scenario: unlimited invite first, then limited invite."""
        with app.app_context():
            self.setup_method()

            # Create unlimited invitation
            unlimited_form = {
                "server_ids": [str(self.server1.id)],
                "unlimited": True,
                "expires": "never",
            }
            unlimited_invite = create_invite(unlimited_form)

            # Create limited invitation
            limited_form = {
                "server_ids": [str(self.server1.id), str(self.server2.id)],
                "unlimited": False,
                "expires": "never",
            }
            limited_invite = create_invite(limited_form)

            mock_client1 = MockMediaClient(media_server=self.server1)
            mock_client2 = MockMediaClient(media_server=self.server2)

            # Create users with unlimited invite - should remain separate
            user1_kwargs = {
                "username": "unlimited_user1",
                "email": "user1@unlimited.com",
                "code": unlimited_invite.code,
                "server_id": self.server1.id,
                "token": "token1",
            }
            unlimited_user1 = mock_client1._create_user_with_identity_linking(
                user1_kwargs
            )

            user2_kwargs = {
                "username": "unlimited_user2",
                "email": "user2@unlimited.com",
                "code": unlimited_invite.code,
                "server_id": self.server1.id,
                "token": "token2",
            }
            unlimited_user2 = mock_client1._create_user_with_identity_linking(
                user2_kwargs
            )

            # Create users with limited invite - should get linked
            user3_kwargs = {
                "username": "limited_user_srv1",
                "email": "user@limited.com",
                "code": limited_invite.code,
                "server_id": self.server1.id,
                "token": "token3",
            }
            limited_user1 = mock_client1._create_user_with_identity_linking(
                user3_kwargs
            )

            # Create identity for limited user (simulating real scenario)
            identity = Identity(
                primary_email="user@limited.com", primary_username="limited_user_srv1"
            )
            db.session.add(identity)
            db.session.flush()
            limited_user1.identity_id = identity.id
            db.session.commit()

            user4_kwargs = {
                "username": "limited_user_srv2",
                "email": "user@limited.com",
                "code": limited_invite.code,
                "server_id": self.server2.id,
                "token": "token4",
            }
            limited_user2 = mock_client2._create_user_with_identity_linking(
                user4_kwargs
            )
            db.session.commit()

            # Verify unlimited users remain separate
            assert unlimited_user1.identity_id is None
            assert unlimited_user2.identity_id is None
            assert (
                unlimited_user1.identity_id == unlimited_user2.identity_id
            )  # Both None

            # Verify limited users are linked
            assert limited_user1.identity_id == limited_user2.identity_id
            assert limited_user1.identity_id is not None

    def test_edge_case_nonexistent_invitation_code(self, app):
        """Test edge case where invitation code doesn't exist in database."""
        with app.app_context():
            self.setup_method()

            mock_client = MockMediaClient(media_server=self.server1)

            # Try to create user with non-existent invitation code
            user_kwargs = {
                "username": "test_user",
                "email": "test@example.com",
                "code": "NONEXISTENT123",  # This code doesn't exist
                "server_id": self.server1.id,
                "token": "token1",
            }

            # Should not crash and should create user without identity linking
            user = mock_client._create_user_with_identity_linking(user_kwargs)
            db.session.commit()

            assert user.identity_id is None
            assert user.code == "NONEXISTENT123"
            assert user.username == "test_user"

    def test_same_user_unlimited_invite_multiple_servers(self, app):
        """Test that the SAME user using unlimited invite across servers gets linked."""
        with app.app_context():
            self.setup_method()

            # Create unlimited invitation for multiple servers
            form_data = {
                "server_ids": [str(self.server1.id), str(self.server2.id)],
                "unlimited": True,
                "expires": "never",
            }
            invitation = create_invite(form_data)

            mock_client1 = MockMediaClient(media_server=self.server1)
            mock_client2 = MockMediaClient(media_server=self.server2)

            # Create first user on server 1 (same person: john@example.com)
            user1_kwargs = {
                "username": "john_jellyfin",
                "email": "john@example.com",  # SAME EMAIL
                "code": invitation.code,
                "server_id": self.server1.id,
                "token": "token1",
            }
            user1 = mock_client1._create_user_with_identity_linking(user1_kwargs)

            # Create identity for first user (simulating what happens in practice)
            identity = Identity(
                primary_email="john@example.com", primary_username="john_jellyfin"
            )
            db.session.add(identity)
            db.session.flush()
            user1.identity_id = identity.id
            db.session.commit()

            # Create second user on server 2 (SAME PERSON: john@example.com)
            user2_kwargs = {
                "username": "john_plex",
                "email": "john@example.com",  # SAME EMAIL
                "code": invitation.code,
                "server_id": self.server2.id,
                "token": "token2",
            }
            user2 = mock_client2._create_user_with_identity_linking(user2_kwargs)
            db.session.commit()

            # FIXED: Same person (email) using unlimited invite across servers should be linked
            print(f"User1 identity_id: {user1.identity_id}")
            print(f"User2 identity_id: {user2.identity_id}")
            print(f"User1 email: {user1.email}")
            print(f"User2 email: {user2.email}")

            # Correct behavior: same person should be linked even with unlimited invite
            assert user1.identity_id == user2.identity_id  # Same person = linked
            assert user1.identity_id is not None
            assert user1.email == user2.email == "john@example.com"

    def test_edge_case_invitation_code_is_none(self, app):
        """Test edge case where invitation code is None."""
        with app.app_context():
            self.setup_method()

            mock_client = MockMediaClient(media_server=self.server1)

            # Create user with empty string code (since code is NOT NULL)
            user_kwargs = {
                "username": "test_user",
                "email": "test@example.com",
                "code": "",  # Empty invitation code (since NULL not allowed)
                "server_id": self.server1.id,
                "token": "token1",
            }

            user = mock_client._create_user_with_identity_linking(user_kwargs)
            db.session.commit()

            assert user.identity_id is None
            assert user.code == ""
            assert user.username == "test_user"
