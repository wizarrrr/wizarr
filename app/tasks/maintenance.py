# app/tasks/maintenance.py
import logging

from app.extensions import scheduler
from app.services.expiry import delete_user_if_expired  # ← fixed import


@scheduler.task("interval", id="check_expiring", minutes=15, misfire_grace_time=900)
def check_expiring():
    app = getattr(scheduler, "app", None)
    if app and hasattr(app, "app_context"):
        with app.app_context():
            deleted = delete_user_if_expired()
            logging.info("Deleted %s expired users.", len(deleted)) if len(
                deleted
            ) > 0 else None
