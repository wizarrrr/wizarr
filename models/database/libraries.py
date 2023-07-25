from peewee import SQL, CharField, DateTimeField
from models.database.base import BaseModel


class Libraries(BaseModel):
    id = CharField(unique=True)
    name = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
