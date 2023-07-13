from peewee import SQL, CharField, DateTimeField
from pydantic import BaseModel as PydanticBaseModel

from .base import BaseModel


class Libraries(BaseModel):
    id = CharField(unique=True)
    name = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])

class LibrariesModel(PydanticBaseModel):
    id: str
    name: str
    created: str