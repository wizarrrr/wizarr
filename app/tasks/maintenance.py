# app/tasks/maintenance.py
import logging
from app.extensions import scheduler
from app.services.expiry import delete_user_if_expired   # ← fixed import

@scheduler.task("interval", id="check_expiring", minutes=15, misfire_grace_time=900)
def check_expiring():
    logging.info("Checking for expiring users…")
    deleted = delete_user_if_expired()
    logging.info("Deleted %s expired users.", len(deleted))
