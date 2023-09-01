from typing import Optional
from flask_restx import Model, fields

class SettingsModel:
    server_type: Optional[str]
    server_verified: Optional[bool]
    server_url: Optional[str]
    server_name: Optional[str]
    discord_id: Optional[str]
    request_type: Optional[str]
    request_url: Optional[str]
    request_api_key: Optional[str]
    server_api_key: Optional[str]
    discord_widget: Optional[str]
    custom_html: Optional[str]

    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self):
        model = {}

        for key, value in self.__dict__.items():
            if key != "_state":
                model[key] = value

        return model

SettingsPostModel = Model('SettingsPostModel', {
    "server_type": fields.String(required=False, description="The type of server"),
    "server_verified": fields.String(required=False, description="Whether the server has been verified"),
    "server_url": fields.String(required=False, description="The URL of the server"),
    "server_name": fields.String(required=False, description="The name of the server"),
    "discord_id": fields.String(required=False, description="The Discord ID of the server"),
    "request_type": fields.String(required=False, description="The type of request server"),
    "request_url": fields.String(required=False, description="The URL of the request server"),
    "request_api_key": fields.String(required=False, description="The API key of the request server"),
    "server_api_key": fields.String(required=False, description="The API key of the server"),
    "discord_widget": fields.String(required=False, description="Whether the Discord widget is enabled"),
    "custom_html": fields.String(required=False, description="Custom HTML to be displayed on the homepage")
})

SettingsGetModel = Model('SettingsGetModel', {
    "server_type": fields.String(required=False, description="The type of server"),
    "server_verified": fields.String(required=False, description="Whether the server has been verified"),
    "server_url": fields.String(required=False, description="The URL of the server"),
    "server_name": fields.String(required=False, description="The name of the server"),
    "discord_id": fields.String(required=False, description="The Discord ID of the server"),
    "request_type": fields.String(required=False, description="The type of request server"),
    "request_url": fields.String(required=False, description="The URL of the request server"),
    "request_api_key": fields.String(required=False, description="The API key of the request server"),
    "server_api_key": fields.String(required=False, description="The API key of the server"),
    "discord_widget": fields.String(required=False, description="Whether the Discord widget is enabled"),
    "custom_html": fields.String(required=False, description="Custom HTML to be displayed on the homepage")
})