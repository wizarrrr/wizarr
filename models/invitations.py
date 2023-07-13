from peewee import SQL, BooleanField, CharField, DateTimeField
from pydantic import BaseModel as PydanticBaseModel

from .base import BaseModel


class Invitations(BaseModel):
    code = CharField()
    used = BooleanField()
    used_at = DateTimeField(null=True)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
    used_by = CharField(null=True)
    expires = DateTimeField(null=True)  # How long the invite is valid for
    unlimited = BooleanField(null=True)
    duration = CharField(null=True)  # How long the membership is kept for
    specific_libraries = CharField(null=True)
    plex_allow_sync = BooleanField(null=True)
    plex_home = BooleanField(null=True)
    
class InvitationsModel(PydanticBaseModel):
    code: str
    used: bool
    used_at: str
    created: str
    used_by: str
    expires: str
    unlimited: bool
    duration: str
    specific_libraries: str
    plex_allow_sync: bool
    plex_home: bool