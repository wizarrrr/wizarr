from app import create_app
from app.extensions import scheduler
from app.scripts.migrate_libraries import run_library_migration, update_server_verified
from app.scripts.migrate_media_server import migrate_single_to_multi


def on_starting(server):
    # this runs once, in the Gunicorn master
    import os

    # Set environment variable to indicate we're in gunicorn context
    os.environ["SERVER_SOFTWARE"] = "gunicorn"

    app = create_app()

    update_server_verified(app)

    run_library_migration(app)

    migrate_single_to_multi(app)

    # Scheduler is already initialized in extensions.py, just start it
    if scheduler._scheduler and not scheduler.running:
        scheduler.start()
        # Determine frequency message based on WIZARR_ENABLE_SCHEDULER (dev mode indicator)
        if os.getenv("WIZARR_ENABLE_SCHEDULER", "false").lower() in (
            "true",
            "1",
            "yes",
        ):
            print(
                "✅ Gunicorn: Scheduler started - expiry cleanup will run every 1 minute (development mode)"
            )
        else:
            print(
                "✅ Gunicorn: Scheduler started - expiry cleanup will run every 15 minutes (production mode)"
            )
