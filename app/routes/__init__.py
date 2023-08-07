from .main import main
from .admin import admin
from .settings import settings
from .home import home
from .authentication import authentication
from .invite import invite
from .wizard import wizard
from .setup import setup
from .modals import modals
from .tables import tables
from .errors import *

from flask import Blueprint
from flask_jwt_extended import current_user
from helpers import get_setting

routes = Blueprint("app", __name__)

@routes.context_processor
def inject_user():
    return {
        "current_user": current_user,
        "server_name": get_setting("server_name", "Wizarr")
    }

routes.register_blueprint(main)
routes.register_blueprint(home)
routes.register_blueprint(admin)
routes.register_blueprint(settings)
routes.register_blueprint(authentication)
routes.register_blueprint(invite)
routes.register_blueprint(wizard)
routes.register_blueprint(setup)
routes.register_blueprint(modals)
routes.register_blueprint(tables)
