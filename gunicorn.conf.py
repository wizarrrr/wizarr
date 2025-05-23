from app import create_app
from app.extensions import scheduler
from app.scripts.migrate_libraries import run_library_migration

def on_starting(server):

    # this runs once, in the Gunicorn master
    app = create_app()

    run_library_migration(app)
    
    scheduler.init_app(app)
    scheduler.start()
