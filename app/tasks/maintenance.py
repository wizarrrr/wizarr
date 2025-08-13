import logging
import os

from app.services.expiry import delete_user_if_expired


def _get_expiry_check_interval():
    """Get the interval for expiry checks based on environment."""
    # Use 1 minute for development, 15 minutes for production
    if os.getenv("WIZARR_ENABLE_SCHEDULER") == "true":
        return 1  # Development mode: every 1 minute
    return 15  # Production mode: every 15 minutes


def check_expiring(app=None):
    """Check for and delete expired users.

    Args:
        app: Flask application instance. If None, will try to get from current context.
    """
    if app is None:
        from flask import current_app

        try:
            app = current_app._get_current_object()
        except RuntimeError:
            # If we're outside application context, we need the app to be passed
            logging.error(
                "check_expiring called outside application context and no app provided"
            )
            return

    with app.app_context():
        deleted = delete_user_if_expired()
        if len(deleted) > 0:
            logging.info("🧹 Expiry cleanup: Deleted %s expired users.", len(deleted))
        else:
            # Only log in development mode to avoid spam in production logs
            if os.getenv("WIZARR_ENABLE_SCHEDULER") == "true":
                logging.info("🕒 Expiry cleanup: No expired users found.")
