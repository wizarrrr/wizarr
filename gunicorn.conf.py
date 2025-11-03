# Gunicorn configuration with clean logging
import logging
import os
import sys

# Add immediate debug to check if config is loaded
print("DEBUG: gunicorn.conf.py loaded!")

# Make log level configurable for debugging production issues
# Set GUNICORN_LOG_LEVEL=info or debug for verbose output
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "warning").lower()
accesslog = None  # Disable access logs for clean output
errorlog = "-"  # Only errors to stderr

# Make workers configurable (default 4, but allow override for resource-constrained systems)
workers = int(os.getenv("GUNICORN_WORKERS", "4"))
worker_class = "sync"

# Worker timeout - kill workers that don't respond within this time
# Increase from default 30s to 120s to account for slow library scans
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))

print(
    f"DEBUG: Gunicorn config - workers={workers}, loglevel={loglevel}, timeout={timeout}s"
)


def on_starting(server):  # noqa: ARG001
    """Called just before the master process is initialized."""
    print("DEBUG: on_starting() hook called!")


def when_ready(server):  # noqa: ARG001
    """Called after the server is started."""
    try:
        print("DEBUG: when_ready() hook called!")

        # Set environment to indicate Gunicorn context
        os.environ["SERVER_SOFTWARE"] = "gunicorn"

        # Only run migrations if we haven't already done so
        if os.getenv("WIZARR_MIGRATIONS_DONE"):
            print("DEBUG: Migrations already done, skipping")
            return

        print("DEBUG: Setting WIZARR_MIGRATIONS_DONE flag")
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

            logger.database_migration(
                "media server migration", "single to multi-server"
            )
            migrate_single_to_multi(app)

            # Check Flask-APScheduler status - it handles Gunicorn coordination automatically
            from app.extensions import scheduler

            print("DEBUG: Checking Flask-APScheduler status...")

            if scheduler and hasattr(scheduler, "scheduler") and scheduler.scheduler:
                if scheduler.running:
                    print("DEBUG: Flask-APScheduler is running")
                    dev_mode = os.getenv(
                        "WIZARR_ENABLE_SCHEDULER", "false"
                    ).lower() in (
                        "true",
                        "1",
                        "yes",
                    )
                    logger.scheduler_status(enabled=True, dev_mode=dev_mode)
                else:
                    print("DEBUG: Flask-APScheduler exists but not running")
                    logger.warning("Scheduler initialized but not running")
            else:
                print("DEBUG: Flask-APScheduler not available")
                logger.info("Scheduler disabled or not initialized")

        # Complete the startup sequence
        logger.complete()

    except Exception as e:
        print(f"DEBUG: Error in when_ready(): {e}")
        import traceback

        traceback.print_exc()


def post_worker_init(worker):
    """Worker process initialization - runs once per worker after spawn."""
    try:
        # Set worker environment
        os.environ["GUNICORN_WORKER_PID"] = str(worker.pid)
        print(f"DEBUG: Worker {worker.pid} initialized successfully")

        # Suppress Flask app creation logs in workers
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        logging.getLogger("app").setLevel(logging.ERROR)
    except Exception as e:
        print(f"ERROR: Worker {worker.pid} failed to initialize: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        raise


def worker_exit(server, worker):  # noqa: ARG001
    """Called when a worker exits (crash or graceful shutdown)."""
    print(f"WARNING: Worker {worker.pid} exited (age: {worker.age}s)")


def worker_abort(worker):
    """Called when a worker receives SIGABRT (usually due to timeout)."""
    print(
        f"ERROR: Worker {worker.pid} aborted (timeout or critical error)",
        file=sys.stderr,
    )
    import traceback

    traceback.print_stack()


def on_exit(server):  # noqa: ARG001
    """Called just before the master process exits."""
    print("INFO: Gunicorn master process shutting down")
