from peewee import SQL, CharField, DateTimeField, IntegerField, ForeignKeyField
from app.models.database.base import BaseModel

class Migrations(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
