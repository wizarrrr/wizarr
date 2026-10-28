import datetime
import logging
import os

from app.services.expiry import (
    disable_or_delete_user_if_expired,
)


def checkpoint_wal_database(app=None):
    """Checkpoint the SQLite WAL file to prevent unbounded growth.

    WAL mode accumulates changes in the -wal file. Periodic checkpointing
    ensures the WAL doesn't grow too large and improves backup reliability.

    This should be called periodically (e.g., daily) via the scheduler.

    Args:
        app: Flask application instance. If None, will try to get from current context.
    """
    if app is None:
        from flask import current_app

        try:
            app = current_app._get_current_object()  # type: ignore
        except RuntimeError:
            logging.error(
                "checkpoint_wal_database called outside application context and no app provided"
            )
            return

    with app.app_context():
        from app.extensions import db

        # Only checkpoint SQLite databases in WAL mode
        if "sqlite" not in str(db.engine.url):
            return

        try:
            # Check if we're actually in WAL mode first
            with db.engine.connect() as conn:
                result = conn.exec_driver_sql("PRAGMA journal_mode").fetchone()
                journal_mode = result[0] if result else "unknown"

                if journal_mode.lower() != "wal":
                    # Not in WAL mode, nothing to checkpoint
                    logging.debug(
                        f"Skipping WAL checkpoint (journal_mode={journal_mode})"
                    )
                    return

                # Execute WAL checkpoint - this merges WAL back into main database
                # PASSIVE mode doesn't block readers/writers
                conn.exec_driver_sql("PRAGMA wal_checkpoint(PASSIVE)")
                logging.info("✅ SQLite WAL checkpoint completed")
        except Exception as e:
            logging.warning(f"Failed to checkpoint WAL: {e}")


# 0x10000: check all tables, not only the tables that this connection used.
# 0x00002: run ANALYZE on the tables that need it.
# The scheduler uses pooled connections, so the "used tables" of one
# connection are random. Thus the daily run also uses 0x10002.
SQLITE_OPTIMIZE_MASK = 0x10002

# Maximum number of index rows that ANALYZE reads. This keeps the run short
# on large tables (SQLite 3.46+ uses the same value for PRAGMA optimize).
SQLITE_ANALYSIS_LIMIT = 400


def optimize_sqlite_database(app=None):
    """Update the SQLite query planner statistics with ``PRAGMA optimize``.

    Without statistics, the query planner can choose a bad index. The
    background leader runs this function once at startup and once a day.

    Args:
        app: Flask application instance. If None, will try to get from current context.
    """
    if app is None:
        from flask import current_app

        try:
            app = current_app._get_current_object()  # type: ignore
        except RuntimeError:
            logging.error(
                "optimize_sqlite_database called outside application context and no app provided"
            )
            return

    with app.app_context():
        from app.extensions import db

        if db.engine.dialect.name != "sqlite":
            return

        try:
            with db.engine.connect() as conn:
                conn.exec_driver_sql(f"PRAGMA analysis_limit={SQLITE_ANALYSIS_LIMIT}")
                conn.exec_driver_sql(f"PRAGMA optimize={SQLITE_OPTIMIZE_MASK:#x}")
                conn.commit()
            logging.info("SQLite PRAGMA optimize completed")
        except Exception as e:
            logging.warning(f"SQLite PRAGMA optimize failed: {e}")


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
        # Only log in development mode to avoid spam in production logs
        elif os.getenv("WIZARR_ENABLE_SCHEDULER") == "true":
            logging.info("🕒 Expiry cleanup: No expired users found.")


def send_expiry_reminders(app=None):
    """Email users whose access expires within the configured reminder window.

    Each user is isolated: a failure for one user is logged and does not
    stop the remaining users, mirroring check_expiring()'s use of
    disable_or_delete_user_if_expired().

    Args:
        app: Flask application instance. If None, will try to get from current context.
    """
    if app is None:
        from flask import current_app

        try:
            app = current_app._get_current_object()  # type: ignore
        except RuntimeError:
            logging.error(
                "send_expiry_reminders called outside application context and no app provided"
            )
            return

    with app.app_context():
        from app.extensions import db
        from app.models import SMTPConfiguration
        from app.services.email import EmailSendError, send_expiry_reminder_email
        from app.services.expiry import get_users_needing_reminder

        config = SMTPConfiguration.query.first()
        if not config or not config.enabled or not config.reminder_days_before:
            return

        users = get_users_needing_reminder(config.reminder_days_before)
        sent = 0
        for user in users:
            try:
                # Database stores naive UTC datetimes.
                user_expires = user.expires
                if user_expires.tzinfo is None:
                    user_expires = user_expires.replace(tzinfo=datetime.UTC)
                now = datetime.datetime.now(datetime.UTC)
                days_left = max(1, round((user_expires - now).total_seconds() / 86400))
                send_expiry_reminder_email(user, days_left)
                user.expiry_reminder_sent_at = datetime.datetime.now(datetime.UTC)
                db.session.commit()
                sent += 1
            except EmailSendError as exc:
                db.session.rollback()
                logging.warning(
                    "Failed to send expiry reminder to user %s: %s", user.id, exc
                )
            except Exception as exc:
                db.session.rollback()
                logging.error(
                    "Unexpected error sending expiry reminder to user %s: %s",
                    user.id,
                    exc,
                )

        if sent:
            logging.info("📧 Sent %s expiry reminder email(s).", sent)
