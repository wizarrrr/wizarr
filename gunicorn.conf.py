from app import create_app
from app.extensions import scheduler
from app.scripts.migrate_libraries import migrate_libraries

def on_starting(server):

    # this runs once, in the Gunicorn master
    app = create_app()

    migrate_libraries(app)
    
    scheduler.init_app(app)
    scheduler.start()
