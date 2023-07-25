from urllib.parse import urlparse

from peewee import SQL, CharField, DateTimeField
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, HttpUrl, constr

from .base import BaseModel


class Libraries(BaseModel):
    id = CharField(unique=True)
    name = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])


class ScanLibraries(PydanticBaseModel):
    server_type: constr(pattern=r'^(jellyfin|plex)$') = Field(description='Type of media server')
    server_url: HttpUrl = Field(description='URL of the media server')
    server_api_key: str = Field(description='API key of the media server')