from urllib.parse import urlparse

from peewee import SQL, CharField, DateTimeField
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, HttpUrl, constr, validator

from .base import BaseModel


class Libraries(BaseModel):
    id = CharField(unique=True)
    name = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])

class LibrariesModel(PydanticBaseModel):
    id: str
    name: str
    created: str
    
class LibrariesPostModel(PydanticBaseModel):
    id: str = Field(description="The ID of the library", min_length=1, max_length=30)
    name: str = Field(description="The name of the library", min_length=1, max_length=30)

class LibrariesListPostModel(PydanticBaseModel):
    libraries: list[str] = Field(description="A list of libraries to add")
    
    
    
class ScanLibraries(PydanticBaseModel):
    server_type: constr(pattern=r'^(jellyfin|plex)$') = Field(description='Type of media server')
    server_url: HttpUrl = Field(description='URL of the media server')
    server_api_key: str = Field(description='API key of the media server')