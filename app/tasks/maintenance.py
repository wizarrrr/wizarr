import logging
import os

from app.services.expiry import (
    disable_or_delete_user_if_expired,
)


def _get_expiry_check_interval():
    """Get the interval for expiry checks based on environment."""
    # Use 1 minute for development, 15 minutes for production
    if os.getenv("WIZARR_ENABLE_SCHEDULER") == "true":
        return 1  # Development mode: every 1 minute
    return 15  # Production mode: every 15 minutes


def check_expiring(app=None):
    """Check for and process expired users based on expiry action setting.

    Args:
        app: Flask application instance. If None, will try to get from current context.
    """
    if app is None:
        from flask import current_app

        try:
            app = current_app._get_current_object()  # type: ignore
        except RuntimeError:
            # If we're outside application context, we need the app to be passed
            logging.error(
                "check_expiring called outside application context and no app provided"
            )
            return

    with app.app_context():
        processed = disable_or_delete_user_if_expired()
        if len(processed) > 0:
            logging.info(
                "🧹 Expiry cleanup: Processed %s expired users.", len(processed)
            )
        else:
            # Only log in development mode to avoid spam in production logs
            if os.getenv("WIZARR_ENABLE_SCHEDULER") == "true":
                logging.info("🕒 Expiry cleanup: No expired users found.")
