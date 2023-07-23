from peewee import IntegrityError
from pydantic import ValidationError
from werkzeug.exceptions import UnsupportedMediaType

from app.exceptions import AuthenticationError
from app.extensions import api

from .accounts_api import api as accounts_api
from .auth_api import api as auth_api
from .invites_api import api as invites_api
from .libraries_api import api as libraries_api
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

# pylint: disable=protected-access
api.title = "Wizarr API"
api.description = "Wizarr API"
api.prefix = "/api"
api.authorizations = authorizations
api._doc = "/api/docs"

def error_handler(exception, code, json=False):
    error_object = {
        "error": {
            "message": str(exception),
            "type": type(exception).__name__
        },
    }

    if json:
        error_object = {**error_object, **exception.json()}
    else:
        error_object = {**error_object, "message": str(exception)}


    return error_object, code


@api.errorhandler(ValidationError)
def handle_validation_error(error):
    return error_handler(error, 400, True)

@api.errorhandler(IntegrityError)
def handle_value_error(error):
    return error_handler(error, 400)

@api.errorhandler(UnsupportedMediaType)
def handle_unsupported_media_type(error):
    return error_handler(error, 415)

@api.errorhandler(AuthenticationError)
def handle_authentication_error(error):
    return error_handler(error, 401)

@api.errorhandler(Exception)
def handle_request_exception(error):
    return error_handler(error, 500)

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
