# app/tasks/maintenance.py
import logging
import os

from app.extensions import scheduler
from app.services.expiry import delete_user_if_expired


def _get_expiry_check_interval():
    """Get the interval for expiry checks based on environment."""
    # Use 1 minute for development, 15 minutes for production
    if os.getenv("WIZARR_ENABLE_SCHEDULER") == "true":
        return 1  # Development mode: every 1 minute
    return 15  # Production mode: every 15 minutes


@scheduler.task(
    "interval",
    id="check_expiring",
    minutes=_get_expiry_check_interval(),
    misfire_grace_time=900,
)
def check_expiring():
    app = getattr(scheduler, "app", None)
    if app and hasattr(app, "app_context"):
        with app.app_context():
            deleted = delete_user_if_expired()
            if len(deleted) > 0:
                logging.info(
                    "🧹 Expiry cleanup: Deleted %s expired users.", len(deleted)
                )
            else:
                # Only log in development mode to avoid spam in production logs
                if os.getenv("WIZARR_ENABLE_SCHEDULER") == "true":
                    logging.info("🕒 Expiry cleanup: No expired users found.")
