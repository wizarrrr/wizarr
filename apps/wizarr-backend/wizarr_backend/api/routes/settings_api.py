from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from peewee import Case, IntegrityError, fn

from app.models.settings import SettingsGetModel, SettingsModel, SettingsPostModel
from app.models.database.settings import Settings
from app.security import is_setup_required

from app.models.database.libraries import Libraries
from app.models.database.users import Users
from app.models.database.invitations import Invitations
from app.models.database.requests import Requests
from helpers.onboarding import populateForServerType, showDiscord


api = Namespace("Settings", description="Settings related operations", path="/settings")

api.add_model("SettingsPostModel", SettingsPostModel)
api.add_model("SettingsGetModel", SettingsGetModel)

@api.route('')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class SettingsListAPI(Resource):

    method_decorators = [] if is_setup_required() else [jwt_required()]

    # @api.marshal_with(SettingsGetModel)
    @api.doc(description="Get all settings")
    @api.response(200, "Successfully retrieved all settings")
    @api.response(500, "Internal server error")
    def get(self):
        result = Settings.select()
        response = { setting.key: setting.value for setting in result }
        return response, 200


    @api.expect(SettingsPostModel)
    @api.marshal_with(SettingsGetModel)
    @api.doc(description="Update all settings")
    @api.response(200, "Successfully updated all settings")
    @api.response(400, "Invalid settings")
    @api.response(500, "Internal server error")
    def post(self):
        # Form data is stored in request.form
        form = request.form.to_dict()

        # Verify that the form data is valid
        data = SettingsModel(**form)

        # Insert the settings into the database as key-value pairs
        settings = data.model_dump()

        for key, value in settings.items():
            Settings.update(key=key, value=value)

        # Get the value of the 'setup' query parameter
        initial_setup = request.args.get('setup') == "true"
        if initial_setup and "server_type" in settings:
            populateForServerType(settings["server_type"])

        if "server_discord_id" in settings:
            showDiscord(bool(settings["server_discord_id"]))

        response = { key: value for key, value in settings.items() }

        return response, 200

    @api.expect(SettingsPostModel)
    @api.marshal_with(SettingsGetModel)
    @api.doc(description="Update all settings")
    @api.response(200, "Successfully updated settings")
    @api.response(400, "Invalid settings")
    @api.response(500, "Internal server error")
    def put(self):
        # Form data is stored in request.form
        form = request.form.to_dict()

        # Verify that the form data is valid
        data = SettingsModel(**form)

        # Extract the data from the model to a dictionary
        settings = data.model_dump()

        # Get the value of the 'setup' query parameter
        initial_setup = request.args.get('setup') == "true"
        if initial_setup and "server_type" in settings:
            populateForServerType(settings["server_type"])

        if "server_discord_id" in settings:
            showDiscord(settings["server_discord_id"] != "")

        # FIXME: This will send many queries to the database
        # Insert the settings into the database
        for key, value in settings.items():
            setting = Settings.get_or_none(Settings.key == key)
            if not setting:
                Settings.create(key=key, value=value)
            else:
                Settings.update(value=value).where(Settings.key == key).execute()

            if key == "server_type":
                Libraries.delete().execute()
                Users.delete().execute()
                Invitations.delete().execute()

                if value == "plex":
                    Requests.delete().where(Requests.service == "jellyseerr").execute()
                elif value == "jellyfin" or value == "emby":
                    Requests.delete().where(Requests.service == "overseerr").execute()

        return settings, 200


@api.route('/<string:setting_id>')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class SettingsAPI(Resource):

    method_decorators = [jwt_required()]

    @api.marshal_with(SettingsGetModel)
    @api.doc(description="Get a setting by ID")
    @api.response(200, "Successfully retrieved the setting")
    @api.response(400, "Invalid setting ID")
    @api.response(404, "Setting not found")
    @api.response(500, "Internal server error")
    def get(self, setting_id: str):
        result = Settings.get_or_none(Settings.key == setting_id)

        if not result:
            raise IntegrityError(f"Setting {setting_id} not found")  # Raise IntegrityError if setting is not found

        response = { result.key: result.value }

        return response, 200


    @api.expect(SettingsPostModel)
    @api.marshal_with(SettingsGetModel)
    @api.doc(description="Update a setting by ID")
    @api.response(200, "Successfully updated the setting")
    @api.response(400, "Invalid setting ID")
    @api.response(404, "Setting not found")
    @api.response(500, "Internal server error")
    def put(self, setting_id: str):
        Settings.update(value=request.data).where(Settings.key == setting_id).execute()

        response = SettingsAPI.get(self, setting_id)

        return response, 200


    @api.doc(description="Delete a setting by ID")
    @api.response(200, "Successfully deleted the setting")
    @api.response(400, "Invalid setting ID")
    @api.response(404, "Setting not found")
    @api.response(500, "Internal server error")
    def delete(self, setting_id: str):
        Settings.delete().where(Settings.key == setting_id).execute()

        response = { "msg": f"Setting {setting_id} deleted successfully" }

        return response, 200
