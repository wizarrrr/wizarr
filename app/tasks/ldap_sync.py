"""LDAP user synchronization background task."""

import logging
import os

logger = logging.getLogger(__name__)


def _get_ldap_sync_interval():
    """Get the interval for LDAP sync based on environment.

    Returns:
        int: Interval in minutes for LDAP sync
    """
    # Check environment variable first
    env_interval = os.getenv("LDAP_SYNC_INTERVAL_MINUTES")
    if env_interval:
        try:
            return int(env_interval)
        except ValueError:
            logger.warning(
                "Invalid LDAP_SYNC_INTERVAL_MINUTES value: %s, using default",
                env_interval,
            )

    # Use 15 minutes for development, 60 minutes (1 hour) for production
    if os.getenv("WIZARR_ENABLE_SCHEDULER") == "true":
        return 15  # Development mode: every 15 minutes
    return 60  # Production mode: every hour


def sync_ldap_users(app=None):
    """Automatically sync all users from LDAP server.

    This task runs periodically to import new LDAP users into Wizarr.
    Existing users are skipped, only new users are imported.

    Args:
        app: Flask application instance. If None, will try to get from current context.
    """
    if app is None:
        from flask import current_app

        try:
            app = current_app._get_current_object()  # type: ignore
        except RuntimeError:
            logger.error(
                "sync_ldap_users called outside application context and no app provided"
            )
            return

    with app.app_context():
        from app.models import LDAPConfiguration, User
        from app.services.ldap.user_sync import import_ldap_user, list_ldap_users

        # Check if LDAP is enabled
        ldap_config = LDAPConfiguration.query.filter_by(enabled=True).first()
        if not ldap_config:
            # LDAP not configured, skip silently
            return

        # Get all LDAP users
        success, result = list_ldap_users()
        if not success:
            logger.warning("LDAP sync failed: %s", result)
            return

        ldap_users = result

        # Import each user that doesn't exist yet
        imported_count = 0
        skipped_count = 0
        error_count = 0

        for ldap_user in ldap_users:
            username = ldap_user["username"]

            # Check if user already exists
            existing = User.query.filter_by(username=username).first()
            if existing:
                skipped_count += 1
                continue

            # Import the user
            import_success, import_msg = import_ldap_user(username)
            if import_success:
                imported_count += 1
                logger.info("LDAP sync: Imported user %s", username)
            else:
                error_count += 1
                logger.warning(
                    "LDAP sync: Failed to import %s: %s", username, import_msg
                )

        # Log summary
        if imported_count > 0:
            logger.info(
                "🔄 LDAP sync: Imported %d new user(s), skipped %d existing, %d error(s)",
                imported_count,
                skipped_count,
                error_count,
            )
        elif os.getenv("WIZARR_ENABLE_SCHEDULER") == "true":
            # Only log in development mode to avoid spam
            logger.info(
                "🔄 LDAP sync: No new users (checked %d LDAP users)",
                len(ldap_users),
            )
