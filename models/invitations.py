from datetime import datetime
from typing import Optional

from peewee import SQL, BooleanField, CharField, DateTimeField
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field

from .base import BaseModel


class Invitations(BaseModel):
    code = CharField(unique=True)
    used = BooleanField(default=False)
    used_at = DateTimeField(null=True, default=None)
    used_by = CharField(null=True, default=None)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
    expires = DateTimeField(null=True, default=None)  # How long the invite is valid for
    unlimited = BooleanField(null=True, default=None)
    duration = CharField(null=True, default=None)  # How long the membership is kept for
    specific_libraries = CharField(default=None, null=True)
    plex_allow_sync = BooleanField(null=True, default=None)
    plex_home = BooleanField(null=True, default=None)


class InvitationsPostModel(PydanticBaseModel):
    code: str = Field(description="The code of the invitation")
    expires: Optional[datetime] = Field(description="When the invitation expires")
    unlimited: bool = Field(description="Whether the invitation is unlimited")
    plex_home: bool = Field(description="Whether the invitation is for Plex Home")
    plex_allow_sync: bool = Field(description="Whether the invitation allows sync")
    duration: int = Field(description="How long the membership is kept for")
    libraries: list[str] = Field(description="A list of libraries the invitation is for")
