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
            from helpers.accounts import create_account

            username = request.form.get("username", None)
            email = request.form.get("email", None)
            password = request.form.get("password", None)
            password_confirm = request.form.get("password_confirm", None)

            user = create_account(
                username=username,
                email=email,
                password=password,
                confirm_password=password_confirm
            )

            return { "message": "Admin user created", "user": user }, 200


        if setup_type == "settings":
            # Import from helpers
            from helpers.settings import get_settings
            from models.database.settings import Settings

            # Settings from request
            new_settings = request.form.to_dict()

            # If setting already exists update it
            settings = get_settings()

            # Valid settings
            valid_settings = [
                "server_name",
                "server_type",
                "server_url",
                "server_api_key"
            ]

            for key, value in new_settings.items():
                if key not in valid_settings:
                    continue

                if key in settings:
                    Settings.update({ Settings.value: value }).where(Settings.key == key).execute()
                else:
                    Settings.create(key=key, value=value)


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
