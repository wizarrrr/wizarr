# This code creates a Flask RESTX API object, which is used to define the API.

from json import dumps
from os import path

from flask import jsonify
from flask_restx import Api, Swagger
from requests import RequestException
from app.exceptions import AuthenticationError

from .accounts_api import api as accounts_api
from .auth_api import api as auth_api
from .invites_api import api as invites_api
from .libraries_api import api as libraries_api
from .live_notifications_api import api as live_notifications_api
from .notifications_api import api as notifications_api
from .plex_api import api as plex_api
from .scan_libraries_api import api as scan_libraries_api
from .sessions_api import api as sessions_api
from .settings_api import api as settings_api
from .setup_api import api as setup_api
from .tasks_api import api as tasks_api
from .users_api import api as users_api

authorizations = {
    "jsonWebToken": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
    },
    "cookieAuth": {
        "type": "apiKey",
        "in": "cookie",
        "name": "session"
    }
}

api: Api = Api(title="Wizarr API",
               description="Wizarr API",
               prefix="/api",
               doc="/api/docs",
               authorizations=authorizations,
               )

@api.errorhandler(AuthenticationError)
def handle_authentication_error(error):
    return { "message": error.message or "Authentication error" }, 401

@api.errorhandler(Exception)
def handle_request_exception(error):
    error_message = str(error)
    status_code = getattr(error, 'status_code', 500)
    file_name = path.basename(error.__traceback__.tb_frame.f_code.co_filename)
    line_number = error.__traceback__.tb_lineno
    error_type = type(error).__name__
    error_object = {
        "error": {
            "message": error_message,
            "status_code": status_code,
            "file": file_name,
            "line": line_number,
            "type": error_type
        },
    }
    return error_object, status_code


# Ordered Alphabetically for easier viewing in Swagger UI
api.add_namespace(accounts_api)
api.add_namespace(auth_api)
api.add_namespace(invites_api)
api.add_namespace(libraries_api)
api.add_namespace(notifications_api)
api.add_namespace(plex_api)
api.add_namespace(scan_libraries_api)
api.add_namespace(setup_api)
api.add_namespace(sessions_api)
api.add_namespace(settings_api)
api.add_namespace(tasks_api)
api.add_namespace(users_api)

# Potentially remove this if it becomes unstable
# api.add_namespace(live_notifications_api)

# TODO: Tasks API
# TODO: API API
# TODO: HTML API
