from app import app

from .main import main
from .admin import admin
from .settings import settings
from .home import home
from .authentication import authentication
from .invite import invite
from .wizard import wizard
from .setup import setup
from .error import *

from flask_jwt_extended import current_user
from helpers import get_setting

@app.context_processor
def inject_user():
    return {
        "current_user": current_user,
        "server_name": get_setting("server_name", "Wizarr")
    }

app.register_blueprint(main)
app.register_blueprint(admin)
app.register_blueprint(settings)
app.register_blueprint(home)
app.register_blueprint(authentication)
app.register_blueprint(invite)
app.register_blueprint(wizard)
app.register_blueprint(setup)
