from peewee import CharField, DateTimeField, IntegerField, SQL
from app.models.database.base import BaseModel

class Requests(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField(unique=True)
    server_id = CharField(default=0) # Future support for multiple servers
    service = CharField()
    url = CharField(unique=True)
    api_key = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
