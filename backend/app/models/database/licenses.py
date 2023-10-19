from peewee import SQL, CharField, DateTimeField, IntegerField
from app.models.database.base import BaseModel

class Licenses(BaseModel):
    id = IntegerField(primary_key=True)
    membership_id = IntegerField()
    key = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
