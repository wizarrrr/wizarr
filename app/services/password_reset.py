"""Service for managing password reset tokens."""

import datetime
import logging
import secrets
import string

from app.extensions import db
from app.models import PasswordResetToken, User

logger = logging.getLogger("wizarr.password_reset")

# Token configuration
TOKEN_LENGTH = 10  # Same as invitation codes
TOKEN_CHARSET = string.ascii_uppercase + string.digits
TOKEN_EXPIRY_HOURS = 24  # Tokens expire after 24 hours


def _generate_reset_code() -> str:
    """Generate a random password reset code (10 characters)."""
    return "".join(secrets.choice(TOKEN_CHARSET) for _ in range(TOKEN_LENGTH))


def create_reset_token(user_id: int) -> PasswordResetToken | None:
    """Create a password reset token for a user.

    Args:
        user_id: The ID of the user to create a reset token for

    Returns:
        PasswordResetToken object if successful, None otherwise
    """
    try:
        # Verify user exists
        user = db.session.get(User, user_id)
        if not user:
            logger.error(
                "[error    ] Cannot create reset token: User %s not found [app.services.password_reset]",
                user_id,
            )
            return None

        # Invalidate any existing unused tokens for this user
        existing_tokens = PasswordResetToken.query.filter_by(
            user_id=user_id, used=False
        ).all()
        for token in existing_tokens:
            token.used = True
            token.used_at = datetime.datetime.now(datetime.UTC)

        # Generate unique code
        code = _generate_reset_code()
        attempts = 0
        max_attempts = 10

        while (
            PasswordResetToken.query.filter_by(code=code).first()
            and attempts < max_attempts
        ):
            code = _generate_reset_code()
            attempts += 1

        if attempts >= max_attempts:
            logger.error(
                "[error    ] Failed to generate unique reset token code after max attempts [app.services.password_reset]"
            )
            return None

        # Create new token
        expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            hours=TOKEN_EXPIRY_HOURS
        )

        token = PasswordResetToken(
            code=code,
            user_id=user_id,
            created_at=datetime.datetime.now(datetime.UTC),
            expires_at=expires_at,
            used=False,
        )

        db.session.add(token)
        db.session.commit()

        logger.info(
            "[info     ] Created password reset token for user %s (ID: %s), expires at %s [app.services.password_reset]",
            user.username,
            user_id,
            expires_at.isoformat(),
        )

        return token

    except Exception as e:
        logger.error(
            "[error    ] Error creating reset token for user %s: %s [app.services.password_reset]",
            user_id,
            e,
        )
        db.session.rollback()
        return None


def get_reset_token(code: str) -> tuple[PasswordResetToken | None, str]:
    """Retrieve and validate a password reset token by code.

    Args:
        code: The reset token code

    Returns:
        Tuple of (PasswordResetToken or None, error_message)
    """
    if not code or len(code) != TOKEN_LENGTH:
        logger.debug(
            "[debug    ] Invalid reset code format: length=%s [app.services.password_reset]",
            len(code) if code else 0,
        )
        return None, "Invalid reset code format"

    # Case-insensitive lookup
    token = PasswordResetToken.query.filter(
        db.func.lower(PasswordResetToken.code) == code.lower()
    ).first()

    if not token:
        logger.debug(
            "[debug    ] Reset code not found: %s [app.services.password_reset]", code
        )
        return None, "Invalid reset code"

    if token.used:
        logger.debug(
            "[debug    ] Reset code already used: %s [app.services.password_reset]",
            code,
        )
        return None, "Reset code has already been used"

    now = datetime.datetime.now(datetime.UTC)
    expires_aware = (
        token.expires_at.replace(tzinfo=datetime.UTC)
        if token.expires_at.tzinfo is None
        else token.expires_at
    )

    if expires_aware <= now:
        logger.debug(
            "[debug    ] Reset code expired: %s (expired at %s) [app.services.password_reset]",
            code,
            expires_aware.isoformat(),
        )
        return None, "Reset code has expired"

    logger.debug(
        "[debug    ] Reset token validated: %s for user_id=%s [app.services.password_reset]",
        code,
        token.user_id,
    )
    return token, "valid"


def use_reset_token(code: str, new_password: str) -> tuple[bool, str]:
    """Use a reset token to change a user's password.

    Args:
        code: The reset token code
        new_password: The new password to set

    Returns:
        Tuple of (success: bool, message: str)
    """
    from app.services.media.service import reset_user_password

    # Validate token
    token, error = get_reset_token(code)
    if not token:
        return False, error

    # Validate password length
    if not (8 <= len(new_password) <= 128):
        logger.debug(
            "[debug    ] Invalid password length: %s chars [app.services.password_reset]",
            len(new_password),
        )
        return False, "Password must be between 8 and 128 characters"

    try:
        logger.info(
            "[info     ] Attempting password reset for user_id=%s using token %s [app.services.password_reset]",
            token.user_id,
            code,
        )

        # Reset the password on the media server
        success = reset_user_password(token.user_id, new_password)

        if success:
            # Mark token as used
            token.used = True
            token.used_at = datetime.datetime.now(datetime.UTC)
            db.session.commit()

            logger.info(
                "[info     ] Password reset successful for user_id=%s using token %s [app.services.password_reset]",
                token.user_id,
                code,
            )
            return True, "Password reset successfully"
        logger.error(
            "[error    ] Password reset failed on media server for user_id=%s [app.services.password_reset]",
            token.user_id,
        )
        return False, "Failed to reset password on media server"

    except Exception as e:
        logger.error(
            "[error    ] Error using reset token %s: %s [app.services.password_reset]",
            code,
            e,
        )
        db.session.rollback()
        return False, "Internal error during password reset"


def cleanup_expired_tokens() -> int:
    """Remove expired and used tokens from the database.

    Returns:
        Number of tokens deleted
    """
    try:
        now = datetime.datetime.now(datetime.UTC)

        # Delete tokens that are either used or expired
        deleted = PasswordResetToken.query.filter(
            db.or_(
                PasswordResetToken.used.is_(True), PasswordResetToken.expires_at <= now
            )
        ).delete()

        db.session.commit()

        if deleted > 0:
            logger.info(
                "[info     ] Cleaned up %s expired/used password reset tokens [app.services.password_reset]",
                deleted,
            )

        return deleted

    except Exception as e:
        logger.error(
            "[error    ] Error cleaning up expired tokens: %s [app.services.password_reset]",
            e,
        )
        db.session.rollback()
        return 0
