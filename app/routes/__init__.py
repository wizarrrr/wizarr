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
from .debug import debug
from .errors import *

from flask import Blueprint, request
from flask_jwt_extended import current_user
from helpers import get_setting

from app.utils.config_loader import load_config

routes = Blueprint("app", __name__)

@routes.context_processor
def inject_user():
    config = load_config("database.json.j2")
    config_objs = {}
    database_data = {}

    default = {
        "current_user": current_user,
        "server_name": get_setting("server_name", "Wizarr")
    }

    def get_table(table_name: str):
        # Loop through all models in the database
        for model in dir(__import__("app.models.database", fromlist=[table_name])):
            # If the model matches the table name, get the table from the database
            if model.lower() == table_name.lower():
                # Get the table from the database
                table = getattr(__import__("app.models.database", fromlist=[table_name]), model)
                return table.select().dicts()


    # Get object from config file where path matches the current path
    for obj in config:
        if "path" in obj and request.path.endswith(obj["path"]):
            config_objs = { **config_objs, obj["id"]: obj }


    # Loop through all objects in data
    for _, obj in config_objs.items():
        # If object has a table key, get the table from the database
        if "tables" in obj and isinstance(obj["tables"], list):
            # Loop through all tables in the object
                for table in obj["tables"]:
                    # Get the table from the database
                    table_data = get_table(table)

                    # If first_only is set to true in obj["options"], only get the first item
                    if "options" in obj and "first_only" in obj["options"] and obj["options"]["first_only"]:
                        table_data = table_data.first()

                    # Add table data to database data
                    database_data = { **database_data, obj["id"]: { table.lower(): table_data } }

    # If object was found, return default with data
    return { **default, **database_data }

@routes.route('/debug-sentry')
def trigger_error():
    division_by_zero = 1 / 0
    return division_by_zero

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
routes.register_blueprint(debug)
