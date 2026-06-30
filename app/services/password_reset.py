"""Service for managing password reset tokens."""

import datetime
import logging
import secrets
import string

from zxcvbn import zxcvbn

from app.extensions import db
from app.models import PasswordResetToken, Settings, User

logger = logging.getLogger("wizarr.password_reset")

# ─── Configuration ────────────────────────────────────────────────────────────
# Token configuration
TOKEN_LENGTH = 10  # Same as invitation codes
TOKEN_CHARSET = string.ascii_uppercase + string.digits
TOKEN_EXPIRY_HOURS = 24  # Tokens expire after 24 hours

# Security Level Mapping (zxcvbn score 0-4)
# 0: Low (too guessable)
# 1: Medium (still guessable)
# 2: High (somewhat safe)
# 3: Extra High (safe)
# 4: Paranoid (very safe)
DEFAULT_SECURITY_LEVEL = 2

# Legacy defaults for backward compatibility during transition
DEFAULT_PASSWORD_RESET_POLICY = {
    "min_length": 8,
    "max_length": 128,
}


# ─── Internal Helpers ─────────────────────────────────────────────────────────
def _generate_reset_code() -> str:
    """Generate a random password reset code (10 characters)."""
    return "".join(secrets.choice(TOKEN_CHARSET) for _ in range(TOKEN_LENGTH))


def _get_bool_setting(key: str, default: bool) -> bool:
    """Read a boolean setting from the database."""
    setting = Settings.query.filter_by(key=key).first()
    if not setting or setting.value is None:
        return default
    return str(setting.value).strip().lower() == "true"


def _get_int_setting(key: str, default: int, minimum: int, maximum: int) -> int:
    """Read an integer setting from the database with bounds."""
    setting = Settings.query.filter_by(key=key).first()
    if not setting or setting.value in (None, ""):
        return default

    try:
        parsed = int(setting.value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(parsed, maximum))


# ─── Password Validation ─────────────────────────────────────────────────────
def get_password_reset_policy() -> dict[str, int]:
    """Return the current password reset policy from settings."""
    min_length = _get_int_setting(
        "password_reset_min_length", DEFAULT_PASSWORD_RESET_POLICY["min_length"], 8, 128
    )
    max_length = _get_int_setting(
        "password_reset_max_length", DEFAULT_PASSWORD_RESET_POLICY["max_length"], 8, 128
    )
    if max_length < min_length:
        max_length = min_length

    security_level = _get_int_setting(
        "password_reset_security_level", DEFAULT_SECURITY_LEVEL, 0, 4
    )

    return {
        "min_length": min_length,
        "max_length": max_length,
        "security_level": security_level,
    }


def validate_password_against_policy(
    password: str,
    policy: dict[str, int] | None = None,
    context_list: list[str] | None = None,
) -> list[str]:
    """Validate a password against the configured strength policy and context.

    Args:
        password: The password to validate
        policy: Optional policy dict (loads from settings if None)
        context_list: Optional list of strings to check against for guessability (e.g. [username, email])

    Returns:
        List of error messages, or empty list if valid
    """
    active_policy = policy or get_password_reset_policy()
    errors: list[str] = []

    min_length = int(active_policy["min_length"])
    max_length = int(active_policy["max_length"])
    required_score = int(active_policy["security_level"])

    # Basic length check
    if not (min_length <= len(password) <= max_length):
        errors.append(
            f"Password must be between {min_length} and {max_length} characters"
        )
        return errors  # Don't bother with zxcvbn if length is wrong

    # Strength check using zxcvbn
    # We pass context_list to user_inputs so zxcvbn can penalize passwords containing them
    results = zxcvbn(password, user_inputs=context_list)
    score = results["score"]

    if score < required_score:
        # Provide feedback based on what's missing
        feedback = results.get("feedback", {})
        warning = feedback.get("warning")
        suggestions = feedback.get("suggestions", [])

        if warning:
            errors.append(warning)
        elif not suggestions:
            errors.append("Password is too weak")

        for suggestion in suggestions:
            errors.append(suggestion)

    # Manual contextual check (extra safety)
    if context_list:
        for item in context_list:
            if not item or len(item) < 3:
                continue
            if item.lower() in password.lower():
                errors.append(f"Password cannot contain your '{item}'")

    return list(dict.fromkeys(errors))  # Remove duplicates while preserving order


# ─── Token Management ─────────────────────────────────────────────────────────
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

    # Validate against policy
    policy = get_password_reset_policy()
    # Contextual info for guessability check
    context = [token.user.username, token.user.email]
    validation_errors = validate_password_against_policy(
        new_password, policy, context_list=context
    )

    if validation_errors:
        logger.debug(
            "[debug    ] Password validation failed for user_id=%s: %s [app.services.password_reset]",
            token.user_id,
            validation_errors,
        )
        return False, "; ".join(validation_errors)

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
