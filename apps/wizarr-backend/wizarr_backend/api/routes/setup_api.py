from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required

from app.security import is_setup_required
from helpers.accounts import create_account

from app.models.database.accounts import Accounts
from app.models.database.settings import Settings

api = Namespace('Setup API', description='Setup related operations', path="/setup")

@api.route('/status', doc=False)
@api.route('/status/', doc=False)
class Setup(Resource):
    """Setup related operations"""

    method_decorators = [] if is_setup_required() else [jwt_required()]

    @api.doc(description="Get the setup status")
    @api.response(200, "Successfully retrieved the setup status")
    @api.response(500, "Internal server error")
    def get(self):
        # Get counts for stages
        # pylint: disable=no-value-for-parameter
        accounts = Accounts.select()
        account_count = accounts.count() or 0

        # Get data from the database for settings
        server_url = Settings.get_or_none(Settings.key == "server_url")
        server_type = Settings.get_or_none(Settings.key == "server_type")
        server_api_key = Settings.get_or_none(Settings.key == "server_api_key")

        # Check if the server settings are set
        settings_set = server_url is not None and server_type is not None and server_api_key is not None

        # Create the response object
        response = {
            "setup_required": is_setup_required(),
            "setup_stage": {
                "accounts": account_count > 0,
                "settings": settings_set
            }
        }

        # Return the setup status
        return response, 200

@api.route('/accounts', doc=False)
@api.route('/accounts/', doc=False)
class SetupAccounts(Resource):
    """Setup related operations"""

    method_decorators = [] if is_setup_required() else [jwt_required()]

    @api.doc(description="Create a new account")
    @api.response(200, "Successfully created a new account")
    @api.response(500, "Internal server error")
    def post(self):
        # Create the account
        user = create_account(
            display_name=request.form.get("display_name"),
            username=request.form.get("username").lower(),
            email=request.form.get("email"),
            password=request.form.get("password"),
            confirm_password=request.form.get("confirm_password"),
            role="admin"
        )

        return { "message": "Account created", "user": user }, 200

@api.route('/exit', doc=False)
@api.route('/exit/', doc=False)
class SetupExit(Resource):
    """Setup related operations"""

    method_decorators = [] if is_setup_required() else [jwt_required()]

    @api.doc(description="Exit the setup")
    @api.response(200, "Successfully exited the setup")
    @api.response(500, "Internal server error")
    def get(self):
        # Get count for accounts
        # pylint: disable=no-value-for-parameter
        account_set = Accounts.select().count() > 0

        # Get data from the database for settings
        server_url = Settings.get_or_none(Settings.key == "server_url")
        server_type = Settings.get_or_none(Settings.key == "server_type")
        server_api_key = Settings.get_or_none(Settings.key == "server_api_key")

        # Check if the server settings are set
        settings_set = server_url is not None and server_type is not None and server_api_key is not None

        # If the accounts and settings are set, exit the setup by setting server_verified to True
        if account_set and settings_set:
            server_verified = Settings.get_or_create(key="server_verified")
            server_verified[0].value = "True"
            server_verified[0].save()

        return { "message": "Setup exited" }, 200
