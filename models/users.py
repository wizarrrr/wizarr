from peewee import SQL, CharField, DateTimeField, IntegerField
from pydantic import BaseModel as PydanticBaseModel, Field
from typing import Optional
from datetime import datetime

from .base import BaseModel


class Users(BaseModel):
    id = IntegerField(primary_key=True)
    token = CharField()  # Plex ID or Jellyfin ID
    username = CharField()
    email = CharField(null=True, default=None)
    code = CharField(null=True, default=None)
    expires = DateTimeField(null=True, default=None)
    auth = CharField(null=True, default=None)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])

class UsersModel(PydanticBaseModel):
    token: str = Field(default=None, validate_default=False, description="The token of the user")
    username: str = Field(default=None, validate_default=False, description="The username of the user")
    email: Optional[str] = Field(default=None, validate_default=False, description="The email of the user")
    code: Optional[str] = Field(default=None, validate_default=False, description="The code of the user")
    expires: datetime = Field(default=None, validate_default=False, description="The expiration date of the user")
    auth: Optional[str] = Field(default=None, validate_default=False, description="The auth of the user")