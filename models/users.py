from peewee import SQL, CharField, DateTimeField, IntegerField
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

class UsersModel:
    token: str
    username: str
    email: Optional[str]
    code: Optional[str]
    expires: datetime
    auth: Optional[str]

    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self):
        model = {}

        for key, value in self.__dict__.items():
            if key != "_state":
                model[key] = value

        return model