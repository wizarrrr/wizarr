from datetime import datetime, timedelta
from logging import info, warning
from random import choices
from string import ascii_uppercase, digits

from flask import jsonify, make_response, redirect, request, session
from flask_jwt_extended import jwt_required
from flask_restx import Model, Namespace, Resource, fields
from playhouse.shortcuts import model_to_dict

api = Namespace('Setup API', description=' related operations', path="/setup")

@api.route('', doc=False)
@api.route('/<string:setup_type>', doc=False)
class Setup(Resource):

    @api.doc(description="Setup the application")
    @api.response(500, "Internal server error")
    def post(self, setup_type):

        valid_setup_types = ["admin", "settings", "scan-libraries", "libraries", "complete"]

        if setup_type not in valid_setup_types:
            return { "message": "Invalid setup type" }, 400


        if setup_type == "admin":
            # Import from helpers
            from helpers.accounts import create_admin_user

            username = request.form.get("username", None)
            email = request.form.get("email", None)
            password = request.form.get("password", None)
            password_confirm = request.form.get("password_confirm", None)

            user = create_admin_user(username, email, password, password_confirm)

            return { "message": "Admin user created", "user": user }, 200


        if setup_type == "settings":
            # Import from helpers
            from helpers.settings import create_settings

            # Allowed settings keys
            allowed = [
                "server_name",
                "server_type",
                "server_url",
                "server_api_key"
            ]

            # Get the settings
            settings = create_settings(request.form.to_dict(), allowed)

            return { "message": "Settings created", "settings": settings }, 200

        if setup_type == "scan-libraries":
            from .scan_libraries_api import ScanLibrariesListAPI

            lib = ScanLibrariesListAPI()
            return lib.post()

        if setup_type == "libraries":
            from .libraries_api import LibrariesListAPI

            lib = LibrariesListAPI()
            return lib.post()

        if setup_type == "complete":
            from helpers.settings import create_settings

            create_settings({
                "server_verified": True,
            })