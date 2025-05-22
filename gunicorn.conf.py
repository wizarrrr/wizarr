from app import create_app
from app.extensions import scheduler


def on_starting(server):
    # this runs once, in the Gunicorn master
    app = create_app()
    scheduler.init_app(app)
    scheduler.start()
