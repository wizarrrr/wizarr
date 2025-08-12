from app import create_app
from app.extensions import scheduler
from app.scripts.migrate_libraries import run_library_migration, update_server_verified
from app.scripts.migrate_media_server import migrate_single_to_multi


def on_starting(server):
    # this runs once, in the Gunicorn master
    import os

    from app.startup_logger import startup_logger

    # Set environment variable to indicate we're in gunicorn context
    os.environ["SERVER_SOFTWARE"] = "gunicorn"

    # Create app (this will run startup sequence)
    app = create_app()

    # Run Gunicorn-specific migrations (show only if startup sequence is running)
    show_migrations = os.getenv("WIZARR_STARTUP_SHOWN") is None

    if show_migrations:
        startup_logger.database_migration(
            "server verification", "verifying media servers"
        )
    update_server_verified(app)

    if show_migrations:
        startup_logger.database_migration(
            "library migration", "updating library structure"
        )
    run_library_migration(app)

    if show_migrations:
        startup_logger.database_migration(
            "media server migration", "single to multi-server"
        )
    migrate_single_to_multi(app)

    # Scheduler is already initialized in extensions.py, just start it
    if scheduler._scheduler and not scheduler.running:
        scheduler.start()
        # Determine frequency message based on WIZARR_ENABLE_SCHEDULER (dev mode indicator)
        dev_mode = os.getenv("WIZARR_ENABLE_SCHEDULER", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        if show_migrations:
            startup_logger.scheduler_status(enabled=True, dev_mode=dev_mode)


def worker_int(worker):
    # this runs once per worker when it starts
    import os

    from app.startup_logger import startup_logger

    # Set environment variable to indicate this is a worker process
    os.environ["GUNICORN_WORKER_PID"] = str(worker.pid)

    # Log worker ready status (will only show for worker processes)
    startup_logger.worker_ready(str(worker.pid))
