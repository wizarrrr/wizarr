from peewee import SQL, CharField, DateTimeField, IntegerField

from .base import BaseModel


class Admins(BaseModel):
    id = IntegerField(primary_key=True)
    username = CharField(unique=True)
    password = CharField()
    email = CharField(null=True, unique=True, default=None)
    last_login = DateTimeField(null=True, default=None)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
    session = CharField(null=True, default=None)
