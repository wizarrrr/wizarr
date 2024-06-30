from peewee import SQL, BooleanField, CharField, DateTimeField
from app.models.database.base import BaseModel


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
    sessions = CharField(null=True, default=None)
    live_tv = BooleanField(null=True, default=None)
    hide_user = BooleanField(null=True, default=True)
    allow_download = BooleanField(null=True, default=None)
