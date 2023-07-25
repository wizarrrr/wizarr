from peewee import SQL, CharField, DateTimeField, IntegerField
from models.database.base import BaseModel


class Notifications(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    type = CharField()
    url = CharField()
    username = CharField(null=True)
    password = CharField(null=True)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
