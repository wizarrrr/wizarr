from typing import Optional

from flask_restx import Model, fields
from peewee import CharField
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, HttpUrl, constr

from .base import BaseModel


class Settings(BaseModel):
    key = CharField()
    value = CharField(null=True)
    
class SettingsModel(PydanticBaseModel):
    server_type: Optional[constr(pattern="^(plex|jellyfin)$")] = Field(default=None, validate_default=False, description="The type of server")
    server_verified: Optional[bool] = Field(default=None, validate_default=False, description="Whether the server has been verified")
    server_url: Optional[str] = Field(default=None, validate_default=False, description="The URL of the server")
    server_name: Optional[str] = Field(default=None, validate_default=False, description="The name of the server")
    discord_id: Optional[str] = Field(default=None, validate_default=False, description="The Discord ID of the server")
    request_url: Optional[str] = Field(default=None, validate_default=False, description="The URL of the request server")
    request_api_key: Optional[str] = Field(default=None, validate_default=False, description="The API key of the request server")
    server_api_key: Optional[str] = Field(default=None, validate_default=False, description="The API key of the server")
    discord_widget: Optional[bool] = Field(default=None, validate_default=False, description="Whether the Discord widget is enabled")
    
SettingsPostModel = Model('SettingsPostModel', {
    "server_type": fields.String(required=False, description="The type of server"),
    "server_verified": fields.Boolean(required=False, description="Whether the server has been verified"),
    "server_url": fields.String(required=False, description="The URL of the server"),
    "server_name": fields.String(required=False, description="The name of the server"),
    "discord_id": fields.String(required=False, description="The Discord ID of the server"),
    "request_url": fields.String(required=False, description="The URL of the request server"),
    "request_api_key": fields.String(required=False, description="The API key of the request server"),
    "server_api_key": fields.String(required=False, description="The API key of the server"),
    "discord_widget": fields.Boolean(required=False, description="Whether the Discord widget is enabled")   
})

SettingsGetModel = Model('SettingsGetModel', {
    "server_type": fields.String(required=False, description="The type of server"),
    "server_verified": fields.Boolean(required=False, description="Whether the server has been verified"),
    "server_url": fields.String(required=False, description="The URL of the server"),
    "server_name": fields.String(required=False, description="The name of the server"),
    "discord_id": fields.String(required=False, description="The Discord ID of the server"),
    "request_url": fields.String(required=False, description="The URL of the request server"),
    "request_api_key": fields.String(required=False, description="The API key of the request server"),
    "server_api_key": fields.String(required=False, description="The API key of the server"),
    "discord_widget": fields.Boolean(required=False, description="Whether the Discord widget is enabled")
})