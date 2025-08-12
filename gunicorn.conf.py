# Gunicorn configuration with clean logging
import logging
import os

# Reduce log level to prevent INFO spam
loglevel = "WARNING"
accesslog = None  # Disable access logs for clean output
errorlog = "-"  # Only errors to stderr

# Standard Gunicorn settings
workers = 4
worker_class = "sync"


def when_ready(server):  # noqa: ARG001
    """Called after the server is started."""
    # Set environment to indicate Gunicorn context
    os.environ["SERVER_SOFTWARE"] = "gunicorn"

    # Only run migrations if we haven't already done so
    if os.getenv("WIZARR_MIGRATIONS_DONE"):
        return

    os.environ["WIZARR_MIGRATIONS_DONE"] = "1"

    # Import here to avoid circular imports
    from app.logging_helpers import AppLogger
    from app.scripts.migrate_libraries import (
        run_library_migration,
        update_server_verified,
    )
    from app.scripts.migrate_media_server import migrate_single_to_multi

    logger = AppLogger("wizarr.master")

    # Get the already-created app from run.py
    import run

    app = run.app

    # Run master-only migrations and setup
    with app.app_context():
        logger.database_migration("server verification", "verifying media servers")
        update_server_verified(app)

        logger.database_migration("library migration", "updating library structure")
        run_library_migration(app)

        logger.database_migration("media server migration", "single to multi-server")
        migrate_single_to_multi(app)

        # Start scheduler (should already be initialized)
        from app.extensions import scheduler

        # Debug: Check scheduler state
        print(
            f"DEBUG: Scheduler state - hasattr(_scheduler): {hasattr(scheduler, '_scheduler')}"
        )
        if hasattr(scheduler, "_scheduler"):
            print(f"DEBUG: _scheduler exists: {scheduler._scheduler is not None}")
            if scheduler._scheduler:
                print(f"DEBUG: Scheduler running: {scheduler.running}")

        if (
            hasattr(scheduler, "_scheduler")
            and scheduler._scheduler
            and not scheduler.running
        ):
            try:
                scheduler.start()
                dev_mode = os.getenv("WIZARR_ENABLE_SCHEDULER", "false").lower() in (
                    "true",
                    "1",
                    "yes",
                )
                logger.scheduler_status(enabled=True, dev_mode=dev_mode)
                print("DEBUG: Successfully started scheduler")
            except Exception as e:
                print(f"DEBUG: Failed to start scheduler: {e}")
                logger.warning(f"Could not start scheduler: {e}")
        else:
            # Show why scheduler wasn't started
            if not hasattr(scheduler, "_scheduler"):
                print("DEBUG: Scheduler not initialized - no _scheduler attribute")
                logger.warning("Scheduler not initialized")
            elif not scheduler._scheduler:
                print("DEBUG: Scheduler _scheduler is None")
                logger.warning("Scheduler instance is None")
            elif scheduler.running:
                print("DEBUG: Scheduler already running")
                logger.success("Scheduler already running")
            else:
                print("DEBUG: Unknown scheduler state")
                logger.warning("Unknown scheduler state")

    # Complete the startup sequence
    logger.complete()


def post_worker_init(worker):
    """Worker process initialization - runs once per worker after spawn."""
    # Set worker environment
    os.environ["GUNICORN_WORKER_PID"] = str(worker.pid)

    # Suppress Flask app creation logs in workers
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    logging.getLogger("app").setLevel(logging.ERROR)
