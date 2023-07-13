# This code creates a Flask RESTX API object, which is used to define the API.

from os import path

from flask_restx import Api

from .accounts_api import api as accounts_api
from .auth_api import api as auth_api
from .notifications_api import api as notifications_api
from .settings_api import api as settings_api

api: Api = Api(title="Wizarr API",
               description="Wizarr API",
               prefix="/api",
               doc="/api/docs")

api.add_namespace(accounts_api)
api.add_namespace(auth_api)
api.add_namespace(notifications_api)
api.add_namespace(settings_api)