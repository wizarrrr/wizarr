from peewee import SQL, CharField, DateTimeField, IntegerField
from app.models.database.base import BaseModel

class Webhooks(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    url = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
