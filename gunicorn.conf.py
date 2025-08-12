# Gunicorn configuration with proper preload and logging
import logging
import os

# Reduce log level to prevent INFO spam
loglevel = "WARNING"
accesslog = None  # Disable access logs for clean output
errorlog = "-"  # Only errors to stderr

# Enable preload_app for proper master/worker separation
preload_app = True
workers = 4
worker_class = "sync"


def on_starting(server):  # noqa: ARG001
    """Gunicorn master process startup - runs once before workers spawn."""
    # Set environment to indicate Gunicorn context
    os.environ["SERVER_SOFTWARE"] = "gunicorn"

    # Import here to avoid circular imports
    from app import create_app
    from app.extensions import scheduler
    from app.logging_helpers import AppLogger
    from app.scripts.migrate_libraries import (
        run_library_migration,
        update_server_verified,
    )
    from app.scripts.migrate_media_server import migrate_single_to_multi

    # Create app instance with startup sequence (happens once)
    logger = AppLogger("wizarr.master")
    app = create_app()

    # Run master-only migrations and setup
    with app.app_context():
        logger.database_migration("server verification", "verifying media servers")
        update_server_verified(app)

        logger.database_migration("library migration", "updating library structure")
        run_library_migration(app)

        logger.database_migration("media server migration", "single to multi-server")
        migrate_single_to_multi(app)

        # Start scheduler in master process
        if scheduler._scheduler and not scheduler.running:
            scheduler.start()
            dev_mode = os.getenv("WIZARR_ENABLE_SCHEDULER", "false").lower() in (
                "true",
                "1",
                "yes",
            )
            logger.scheduler_status(enabled=True, dev_mode=dev_mode)

    logger.complete()


def post_worker_init(worker):
    """Worker process initialization - runs once per worker after spawn."""
    # Set worker environment
    os.environ["GUNICORN_WORKER_PID"] = str(worker.pid)

    # Suppress Flask app creation logs in workers
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    logging.getLogger("app").setLevel(logging.ERROR)
