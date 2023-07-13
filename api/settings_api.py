from flask import make_response
from flask_restx import Namespace, Resource
from peewee import IntegrityError
from pydantic import BaseModel, Field

from api.helpers import try_catch
from models import Settings

api = Namespace("Settings", description="Settings related operations", path="/settings")

@api.route('/')
class SettingsListAPI(Resource):
    
    @try_catch
    def get(self):
        result = Settings.select()
        return { setting.key: setting.value for setting in result }
    
    @try_catch
    def post(self):
        class Post(BaseModel):
            data: dict[str, str] = Field(description="The settings to update")
         
        settings = { key: value for key, value in self.request.form.items() }
        
        Post(data=settings)
        
        for key, value in settings.items():
            Settings.get_or_create(key=key)
            Settings.update(value=value).where(Settings.key == key).execute()
         
        return self._get_all()


@api.route('/<path:setting_id>')
class SettingsAPI(Resource):
    
    @try_catch
    def get(self, setting_id: str):
        class GetByID(BaseModel):
            id: str = Field(description="The ID of the setting to get")

        GetByID(id=setting_id)

        result = Settings.get_or_none(Settings.key == setting_id)

        if not result:
            raise IntegrityError(f"Setting {setting_id} not found")  # Raise IntegrityError if setting is not found

        return { result.key: result.value }
    
    @try_catch
    def put(self, setting_id: str):
        class Put(BaseModel):
            id: str = Field(description="The ID of the setting to update")
            data: dict[str, str] = Field(description="The settings to update")
        
        Put(id=setting_id, data=self.request.data)
    
        Settings.update(value=self.request.data).where(Settings.key == setting_id).execute()
        
        return SettingsAPI.get(self, setting_id)

    @try_catch
    def delete(self, setting_id: str):
        class Delete(BaseModel):
            id: str = Field(description="The ID of the setting to delete")
            
        Delete(id=setting_id)
         
        Settings.delete().where(Settings.key == setting_id).execute()

        return make_response({ "success": True })