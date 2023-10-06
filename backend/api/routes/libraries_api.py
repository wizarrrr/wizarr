
from json import loads
from logging import info
from typing import Optional

from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from helpers.libraries import get_libraries
from app.models.wizarr.libraries import LibrariesModel
from app.security import is_setup_required

api = Namespace('Libraries', description='Libraries related operations', path="/libraries")

@api.route('')
class LibrariesListAPI(Resource):
    """API resource for all libraries"""

    method_decorators = [] if is_setup_required() else [jwt_required()]

    @api.doc(description="Get all libraries")
    @api.response(200, "Successfully retrieved all libraries")
    @api.response(500, "Internal server error")
    def get(self):
        # Get all libraries
        return get_libraries(), 200


    @api.doc(description="")
    @api.response(500, "Internal server error")
    def post(self):
        # Get the libraries from the request
        libraries = LibrariesModel(request.form)

        # Update the libraries in the database
        libraries.update_libraries()

        # Create the response
        response = { "message": "Libraries updated", "libraries": libraries.libraries }

        return response, 200
