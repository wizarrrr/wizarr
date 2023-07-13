from peewee import SQL, CharField, DateTimeField, IntegerField
from pydantic import BaseModel as PydanticBaseModel

from .base import BaseModel


class Admins(BaseModel):
    id = IntegerField(primary_key=True)
    username = CharField(unique=True)
    password = CharField()
    email = CharField(null=True, unique=True, default=None)
    last_login = DateTimeField(null=True, default=None)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
    session = CharField(null=True, default=None)

class AdminsModel(PydanticBaseModel):
    id: int
    username: str
    password: str
    email: str
    last_login: str
    created: str
    session: str