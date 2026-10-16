"""Tests for the password reset tokens, routes, and API endpoint."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.models import MediaServer, PasswordResetToken, User
from app.services.password_reset import create_reset_token, get_reset_token


@pytest.fixture
def make_user(session):
    """Return a function that adds a Jellyfin user to the database."""
    server = MediaServer(
        name="Test Jellyfin",
        server_type="jellyfin",
        url="http://localhost:8096",
        api_key="test-key",
    )
    session.add(server)
    session.commit()

    def make(username="testuser"):
        user = User(
            username=username,
            email=f"{username}@example.com",
            token=f"{username}-token",
            code=username.upper(),
            server_id=server.id,
        )
        session.add(user)
        session.commit()
        return user

    return make


@pytest.fixture
def user(make_user):
    return make_user()


def _add_token(session, user, code, *, expires_in, used=False):
    now = datetime.now(UTC)
    token = PasswordResetToken(
        code=code,
        user_id=user.id,
        created_at=now,
        expires_at=now + expires_in,
        used=used,
        used_at=now if used else None,
    )
    session.add(token)
    session.commit()
    return token


class TestPasswordResetTokenGeneration:
    def test_create_reset_token_basic(self, user):
        token = create_reset_token(user.id)

        assert token is not None
        assert len(token.code) == 10  # TOKEN_LENGTH
        assert token.user_id == user.id
        assert token.used is False

        now = datetime.now(UTC)
        token_expires = token.expires_at
        if token_expires.tzinfo is None:
            token_expires = token_expires.replace(tzinfo=UTC)

        assert now < token_expires <= now + timedelta(hours=25)

    def test_create_reset_token_invalidates_old_tokens(self, session, user):
        token1 = create_reset_token(user.id)
        assert token1 is not None
        token1_code = token1.code

        token2 = create_reset_token(user.id)
        assert token2 is not None

        session.refresh(token1)
        assert token1.used is True
        assert token1.used_at is not None
        assert token2.used is False
        assert token2.code != token1_code

    def test_create_reset_token_nonexistent_user(self, session):
        assert create_reset_token(99999) is None

    def test_tokens_of_other_users_stay_valid(self, make_user):
        """A new token for one user does not invalidate the tokens of other users."""
        users = [make_user(f"user{i}") for i in range(3)]
        tokens = [create_reset_token(u.id) for u in users]

        assert len({t.code for t in tokens}) == len(tokens)
        for token in tokens:
            retrieved, error = get_reset_token(token.code)
            assert retrieved is not None
            assert error == "valid"


class TestPasswordResetTokenValidation:
    def test_get_valid_token(self, user):
        created_token = create_reset_token(user.id)
        assert created_token is not None

        token, error = get_reset_token(created_token.code)

        assert token is not None
        assert error == "valid"
        assert token.code == created_token.code

    def test_get_invalid_code(self, session):
        token, error = get_reset_token("NOTEXIST12")

        assert token is None
        assert error == "Invalid reset code"

    def test_get_expired_token(self, session, user):
        _add_token(session, user, "EXPIRED123", expires_in=timedelta(hours=-1))

        token, error = get_reset_token("EXPIRED123")

        assert token is None
        assert error == "Reset code has expired"

    def test_get_used_token(self, session, user):
        _add_token(
            session, user, "USEDTOKEN1", expires_in=timedelta(hours=24), used=True
        )

        token, error = get_reset_token("USEDTOKEN1")

        assert token is None
        assert error == "Reset code has already been used"

    @pytest.mark.parametrize("code", ["AB", "A" * 50])
    def test_invalid_code_length(self, session, code):
        token, error = get_reset_token(code)

        assert token is None
        assert error == "Invalid reset code format"

    @pytest.mark.parametrize(
        ("expires_in", "used", "expected"),
        [
            (timedelta(hours=24), False, True),
            (timedelta(seconds=1), False, True),
            (timedelta(hours=24), True, False),
            (timedelta(hours=-1), False, False),
            (timedelta(seconds=-1), False, False),
        ],
    )
    def test_token_is_valid_method(self, expires_in, used, expected):
        now = datetime.now(UTC)
        token = PasswordResetToken(
            code="VALID12345",
            user_id=1,
            created_at=now,
            expires_at=now + expires_in,
            used=used,
        )

        assert token.is_valid() is expected


class TestPasswordResetAPIEndpoints:
    def test_create_reset_token_endpoint(self, admin_client, user):
        response = admin_client.post(f"/api/users/{user.id}/reset-password")

        assert response.status_code == 200
        data = response.get_json()
        token = PasswordResetToken.query.filter_by(user_id=user.id, used=False).one()
        assert data["code"] == token.code
        assert data["url"] == f"/reset/{token.code}"
        assert "expires_at" in data

    def test_create_reset_token_nonexistent_user(self, admin_client):
        response = admin_client.post("/api/users/99999/reset-password")

        assert response.status_code == 404

    def test_reset_password_modal_jellyfin_user(self, admin_client, user):
        response = admin_client.get(f"/users/{user.id}/reset-password-modal")

        assert response.status_code == 200
        assert b"Generate Password Reset Link" in response.data

    def test_generate_reset_link_endpoint(self, admin_client, user):
        response = admin_client.post(f"/users/{user.id}/generate-reset-link")

        assert response.status_code == 200
        token = PasswordResetToken.query.filter_by(user_id=user.id, used=False).one()
        assert token.code.encode() in response.data
        assert user.username.encode() in response.data

    def test_reset_password_form_valid_token(self, client, user):
        token = create_reset_token(user.id)
        assert token is not None

        response = client.get(f"/reset/{token.code}")

        assert response.status_code == 200
        assert b"Choose a new password" in response.data
        assert user.username.encode() in response.data

    def test_reset_password_form_invalid_token(self, client, session):
        response = client.get("/reset/INVALID123")

        assert response.status_code == 200
        assert b"This password reset link is invalid." in response.data

    def test_reset_password_post_sets_new_password(self, client, session, user):
        """A POST to /reset/<code> sets the password on the media server once."""
        token = create_reset_token(user.id)
        assert token is not None
        code = token.code
        media_client = MagicMock()
        media_client.reset_password.return_value = True
        form = {"new_password": "NewPass1234", "confirm_password": "NewPass1234"}

        with patch(
            "app.services.media.service.get_client_for_media_server",
            return_value=media_client,
        ):
            response = client.post(f"/reset/{code}", data=form)
            second = client.post(f"/reset/{code}", data=form)

        assert response.status_code == 200
        assert b"Password Reset Successful!" in response.data
        media_client.reset_password.assert_called_once_with(
            "testuser-token", "NewPass1234"
        )
        session.refresh(token)
        assert token.used is True
        assert token.used_at is not None
        # The code works only one time.
        assert b"This password reset link has already been used." in second.data

    def test_reuse_existing_valid_token(self, admin_client, user):
        """The modal shows the existing valid token and does not make a new one."""
        token1 = create_reset_token(user.id)
        assert token1 is not None
        code1 = token1.code

        response = admin_client.get(f"/users/{user.id}/reset-password-modal")

        assert response.status_code == 200
        assert code1.encode() in response.data
        tokens = PasswordResetToken.query.filter_by(user_id=user.id, used=False).all()
        assert [t.code for t in tokens] == [code1]
