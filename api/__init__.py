# This code creates a Flask RESTX API object, which is used to define the API.

from json import dumps
from os import path

from flask_restx import Api, Swagger

from .accounts_api import api as accounts_api
from .auth_api import api as auth_api
from .notifications_api import api as notifications_api
from .sessions_api import api as sessions_api
from .settings_api import api as settings_api
from .tasks_api import api as tasks_api

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

# Ordered Alphabetically for easier viewing in Swagger UI
api.add_namespace(accounts_api)
api.add_namespace(auth_api)
api.add_namespace(notifications_api)
api.add_namespace(sessions_api)
api.add_namespace(settings_api)
api.add_namespace(tasks_api)

# TODO: Tasks API
# TODO: API API
# TODO: HTML API
