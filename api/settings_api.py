from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from peewee import IntegrityError
from pydantic import BaseModel, Field

from api.helpers import try_catch
from models import IdentityModel
from models.settings import (Settings, SettingsGetModel, SettingsModel,
                             SettingsPostModel)

api = Namespace("Settings", description="Settings related operations", path="/settings")

api.add_model("SettingsPostModel", SettingsPostModel)
api.add_model("SettingsGetModel", SettingsGetModel)

@api.route('/')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class SettingsListAPI(Resource):
    
    method_decorators = [try_catch, jwt_required()]

    @api.marshal_with(SettingsGetModel)
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
        
        # Extract the data from the model
        settings = data.model_dump(exclude_defaults=True, exclude_unset=True, exclude_none=True)
        
        # Insert the settings into the database as key-value pairs
        for key, value in settings.items():
            Settings.update(key=key, value=value)

        response = { key: value for key, value in settings.items() }
        
        return response, 200
    
    
    
@api.route('/<string:setting_id>')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class SettingsAPI(Resource):
    
    method_decorators = [try_catch, jwt_required()]

    @api.marshal_with(SettingsGetModel)
    @api.doc(description="Get a setting by ID")
    @api.response(200, "Successfully retrieved the setting")
    @api.response(400, "Invalid setting ID")
    @api.response(404, "Setting not found")
    @api.response(500, "Internal server error")
    def get(self, setting_id: str):
        form = IdentityModel(id=setting_id)

        result = Settings.get_or_none(Settings.key == form.id)

        if not result:
            raise IntegrityError(f"Setting {form.id} not found")  # Raise IntegrityError if setting is not found

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
        class Put(BaseModel):
            id: str = Field(description="The ID of the setting to update")
            data: dict[str, str] = Field(description="The settings to update")
        
        Put(id=setting_id, data=self.request.data)
    
        Settings.update(value=self.request.data).where(Settings.key == setting_id).execute()
        
        response = SettingsAPI.get(self, setting_id)
        
        return response, 200


    @api.doc(description="Delete a setting by ID")
    @api.response(200, "Successfully deleted the setting")
    @api.response(400, "Invalid setting ID")
    @api.response(404, "Setting not found")
    @api.response(500, "Internal server error")
    def delete(self, setting_id: str):
        class Delete(BaseModel):
            id: str = Field(description="The ID of the setting to delete")
            
        Delete(id=setting_id)
         
        Settings.delete().where(Settings.key == setting_id).execute()

        response = { "message": f"Setting {setting_id} deleted successfully" }
        
        return response, 200