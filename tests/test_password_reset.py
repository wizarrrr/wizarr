"""
Unit and integration tests for password reset functionality.

Tests cover:
- Token generation and validation
- Password reset flow
- Token expiry
- Token reuse prevention
- API endpoints
- Security edge cases
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.extensions import db
from app.models import MediaServer, PasswordResetToken, User
from app.services.password_reset import create_reset_token, get_reset_token


class TestPasswordResetTokenGeneration:
    """Test password reset token generation."""

    def test_create_reset_token_basic(self, app):
        """Test creating a basic password reset token."""
        with app.app_context():
            # Create server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Create reset token
            token = create_reset_token(user.id)

            assert token is not None
            assert token.code is not None
            assert len(token.code) == 10  # TOKEN_LENGTH
            assert token.user_id == user.id
            assert token.used is False

            # Ensure both datetimes are timezone-aware for comparison
            now = datetime.now(UTC)
            token_expires = token.expires_at
            if token_expires.tzinfo is None:
                token_expires = token_expires.replace(tzinfo=UTC)

            assert token_expires > now
            expires_limit = now + timedelta(hours=25)
            assert token_expires <= expires_limit

    def test_create_reset_token_invalidates_old_tokens(self, app):
        """Test that creating a new token invalidates old unused tokens."""
        with app.app_context():
            # Create server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Create first token
            token1 = create_reset_token(user.id)
            token1_code = token1.code

            # Create second token
            token2 = create_reset_token(user.id)

            # Refresh token1 from database
            db.session.refresh(token1)

            # First token should be marked as used
            assert token1.used is True
            assert token1.used_at is not None

            # Second token should be active
            assert token2.used is False
            assert token2.code != token1_code

    def test_create_reset_token_nonexistent_user(self, app):
        """Test that creating a token for nonexistent user fails."""
        with app.app_context():
            token = create_reset_token(99999)
            assert token is None

    def test_reset_token_code_uniqueness(self, app):
        """Test that generated token codes are unique."""
        with app.app_context():
            # Create server and users
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user1 = User(
                username="user1",
                email="user1@example.com",
                token="token1",
                code="INVITE1",
                server_id=server.id,
            )
            user2 = User(
                username="user2",
                email="user2@example.com",
                token="token2",
                code="INVITE2",
                server_id=server.id,
            )
            db.session.add_all([user1, user2])
            db.session.commit()

            # Create tokens for both users
            token1 = create_reset_token(user1.id)
            token2 = create_reset_token(user2.id)

            assert token1.code != token2.code


class TestPasswordResetTokenValidation:
    """Test password reset token validation."""

    def test_get_valid_token(self, app):
        """Test retrieving a valid unused token."""
        with app.app_context():
            # Create server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Create token
            created_token = create_reset_token(user.id)

            # Retrieve token
            token, error = get_reset_token(created_token.code)

            assert token is not None
            # When token is valid, error contains "valid" not None
            assert "valid" in error.lower() or error == ""
            assert token.code == created_token.code

    def test_get_invalid_code(self, app):
        """Test retrieving a non-existent token code."""
        with app.app_context():
            token, error = get_reset_token("NOTEXIST12")

            assert token is None
            assert error == "Invalid reset code"

    def test_get_expired_token(self, app):
        """Test that expired tokens are rejected."""
        with app.app_context():
            # Create server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Create expired token
            token = PasswordResetToken(
                code="EXPIRED123",
                user_id=user.id,
                created_at=datetime.now(UTC) - timedelta(hours=25),
                expires_at=datetime.now(UTC) - timedelta(hours=1),
                used=False,
            )
            db.session.add(token)
            db.session.commit()

            # Try to retrieve expired token
            retrieved_token, error = get_reset_token(token.code)

            assert retrieved_token is None
            assert error == "Reset code has expired"

    def test_get_used_token(self, app):
        """Test that used tokens are rejected."""
        with app.app_context():
            # Create server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Create used token
            token = PasswordResetToken(
                code="USEDTOKEN1",  # Exactly 10 chars
                user_id=user.id,
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(hours=24),
                used=True,
                used_at=datetime.now(UTC),
            )
            db.session.add(token)
            db.session.commit()

            # Try to retrieve used token
            retrieved_token, error = get_reset_token(token.code)

            assert retrieved_token is None
            assert error == "Reset code has already been used"

    def test_invalid_code_length(self, app):
        """Test that codes with invalid length are rejected."""
        with app.app_context():
            # Too short
            token, error = get_reset_token("AB")
            assert token is None
            assert error == "Invalid reset code format"

            # Too long
            token, error = get_reset_token("A" * 50)
            assert token is None
            assert error == "Invalid reset code format"

    def test_token_is_valid_method(self, app):
        """Test the is_valid() method on PasswordResetToken."""
        with app.app_context():
            # Create server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Valid token
            valid_token = PasswordResetToken(
                code="VALID12345",
                user_id=user.id,
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(hours=24),
                used=False,
            )
            assert valid_token.is_valid() is True

            # Used token
            used_token = PasswordResetToken(
                code="USED123456",
                user_id=user.id,
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(hours=24),
                used=True,
            )
            assert used_token.is_valid() is False

            # Expired token
            expired_token = PasswordResetToken(
                code="EXPIRED123",
                user_id=user.id,
                created_at=datetime.now(UTC) - timedelta(hours=25),
                expires_at=datetime.now(UTC) - timedelta(hours=1),
                used=False,
            )
            assert expired_token.is_valid() is False


class TestPasswordResetAPIEndpoints:
    """Test password reset API endpoints."""

    def test_create_reset_token_endpoint(self, app, client):
        """Test the API endpoint for creating reset tokens."""
        with app.app_context():
            # Create admin account with unique username
            from app.models import AdminAccount

            admin = AdminAccount(username="admin_test_create_token")
            admin.set_password("password123")
            db.session.add(admin)
            db.session.commit()

            # Create server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Login as admin
            client.post(
                "/login",
                data={"username": "admin_test_create_token", "password": "password123"},
            )

            # Call reset password endpoint
            response = client.post(f"/api/users/{user.id}/reset-password")

            assert response.status_code == 200
            data = response.get_json()
            assert "code" in data
            assert "url" in data
            assert "expires_at" in data
            assert data["url"].startswith("/reset/")

    def test_create_reset_token_nonexistent_user(self, app, client):
        """Test creating reset token for non-existent user."""
        with app.app_context():
            # Create admin account with unique username
            from app.models import AdminAccount

            admin = AdminAccount(username="admin_test_nonexistent")
            admin.set_password("password123")
            db.session.add(admin)
            db.session.commit()

            # Login as admin
            client.post(
                "/login",
                data={"username": "admin_test_nonexistent", "password": "password123"},
            )

            # Call reset password endpoint with invalid user ID
            response = client.post("/api/users/99999/reset-password")

            assert response.status_code == 404

    def test_reset_password_modal_jellyfin_user(self, app, client):
        """Test reset password modal endpoint for Jellyfin user."""
        with app.app_context():
            # Create admin account with unique username
            from app.models import AdminAccount

            admin = AdminAccount(username="admin_test_modal")
            admin.set_password("password123")
            db.session.add(admin)
            db.session.commit()

            # Create Jellyfin server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Login as admin
            client.post(
                "/login",
                data={"username": "admin_test_modal", "password": "password123"},
            )

            # Get modal
            response = client.get(f"/users/{user.id}/reset-password-modal")

            assert response.status_code == 200
            assert (
                b"Generate Password Reset Link" in response.data
                or b"Password Reset Link" in response.data
            )

    def test_generate_reset_link_endpoint(self, app, client):
        """Test the generate reset link endpoint."""
        with app.app_context():
            # Create admin account with unique username
            from app.models import AdminAccount

            admin = AdminAccount(username="admin_test_generate")
            admin.set_password("password123")
            db.session.add(admin)
            db.session.commit()

            # Create server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Login as admin
            client.post(
                "/login",
                data={"username": "admin_test_generate", "password": "password123"},
            )

            # Generate reset link
            response = client.post(f"/users/{user.id}/generate-reset-link")

            assert response.status_code == 200
            assert b"Password Reset Link" in response.data
            assert user.username.encode() in response.data

    def test_reset_password_form_valid_token(self, app, client):
        """Test accessing the reset password form with valid token."""
        with app.app_context():
            # Create server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Create reset token
            token = create_reset_token(user.id)

            # Access reset form
            response = client.get(f"/reset/{token.code}")

            assert response.status_code == 200
            assert (
                b"Choose a new password" in response.data
                or b"Reset Password" in response.data
            )

    def test_reset_password_form_invalid_token(self, app, client):
        """Test accessing the reset password form with invalid token."""
        with app.app_context():
            # Access reset form with invalid code
            response = client.get("/reset/INVALID123")

            assert response.status_code == 200
            assert (
                b"Password Reset Error" in response.data
                or b"invalid" in response.data.lower()
            )


class TestPasswordResetSecurityEdgeCases:
    """Test security edge cases in password reset."""

    def test_token_single_use(self, app):
        """Test that tokens can only be used once."""
        with app.app_context():
            # Create server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Create token
            token = create_reset_token(user.id)
            code = token.code

            # First use - should work
            retrieved1, error1 = get_reset_token(code)
            assert retrieved1 is not None
            # Error contains "valid" when successful
            assert "valid" in error1.lower() or error1 == ""

            # Mark as used
            retrieved1.used = True
            retrieved1.used_at = datetime.now(UTC)
            db.session.commit()

            # Second use - should fail
            retrieved2, error2 = get_reset_token(code)
            assert retrieved2 is None
            assert error2 == "Reset code has already been used"

    def test_multiple_users_concurrent_tokens(self, app):
        """Test that multiple users can have active tokens simultaneously."""
        with app.app_context():
            # Create server
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            # Create multiple users
            users = []
            for i in range(5):
                user = User(
                    username=f"user{i}",
                    email=f"user{i}@example.com",
                    token=f"token{i}",
                    code=f"INVITE{i}",
                    server_id=server.id,
                )
                users.append(user)
                db.session.add(user)
            db.session.commit()

            # Create tokens for all users
            tokens = []
            for user in users:
                token = create_reset_token(user.id)
                tokens.append(token)

            # All tokens should be valid
            for token in tokens:
                retrieved, error = get_reset_token(token.code)
                assert retrieved is not None
                # Error contains "valid" when successful
                assert "valid" in error.lower() or error == ""

    def test_token_expiry_boundary(self, app):
        """Test token expiry at exact boundary."""
        with app.app_context():
            # Create server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Create token that expires in 1 second
            now = datetime.now(UTC)
            token = PasswordResetToken(
                code="BOUNDARY12",
                user_id=user.id,
                created_at=now,
                expires_at=now + timedelta(seconds=1),
                used=False,
            )
            db.session.add(token)
            db.session.commit()

            # Should be valid immediately
            assert token.is_valid() is True

            # Create token that just expired
            expired_token = PasswordResetToken(
                code="JUSTEXPIRE",
                user_id=user.id,
                created_at=now - timedelta(hours=24),
                expires_at=now - timedelta(seconds=1),
                used=False,
            )
            db.session.add(expired_token)
            db.session.commit()

            # Should be invalid
            assert expired_token.is_valid() is False

    def test_reuse_existing_valid_token(self, app, client):
        """Test that opening modal shows existing valid token instead of creating new one."""
        with app.app_context():
            # Create admin account with unique username
            from app.models import AdminAccount

            admin = AdminAccount(username="admin_test_reuse")
            admin.set_password("password123")
            db.session.add(admin)
            db.session.commit()

            # Create server and user
            server = MediaServer(
                name="Test Jellyfin",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
            db.session.add(server)
            db.session.flush()

            user = User(
                username="testuser",
                email="test@example.com",
                token="test-token",
                code="INVITE123",
                server_id=server.id,
            )
            db.session.add(user)
            db.session.commit()

            # Create initial token
            token1 = create_reset_token(user.id)
            code1 = token1.code

            # Login as admin
            client.post(
                "/login",
                data={"username": "admin_test_reuse", "password": "password123"},
            )

            # Open modal - should show existing token
            response = client.get(f"/users/{user.id}/reset-password-modal")

            assert response.status_code == 200
            assert code1.encode() in response.data

            # Check that no new token was created
            tokens = PasswordResetToken.query.filter_by(
                user_id=user.id, used=False
            ).all()
            assert len(tokens) == 1
            assert tokens[0].code == code1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
