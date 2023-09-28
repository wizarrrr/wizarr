from peewee import CharField, DateTimeField, IntegerField, SQL
from app.models.database.base import BaseModel

class Requests(BaseModel):
    id = IntegerField(primary_key=True)
    service = CharField()
    url = CharField()
    api_key = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
