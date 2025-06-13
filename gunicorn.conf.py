from app import create_app
from app.extensions import scheduler
from app.scripts.migrate_libraries import run_library_migration, update_server_verified
from app.scripts.migrate_media_server import migrate_single_to_multi

def on_starting(server):

    # this runs once, in the Gunicorn master
    app = create_app()

    update_server_verified(app)

    run_library_migration(app)
    
    migrate_single_to_multi(app)
    
    scheduler.init_app(app)
    scheduler.start()
