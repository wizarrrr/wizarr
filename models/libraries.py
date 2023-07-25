from urllib.parse import urlparse

from peewee import SQL, CharField, DateTimeField

from .base import BaseModel


class Libraries(BaseModel):
    id = CharField(unique=True)
    name = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
