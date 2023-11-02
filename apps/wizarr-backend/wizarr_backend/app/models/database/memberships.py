from peewee import SQL, CharField, DateTimeField, IntegerField
from app.models.database.base import BaseModel

class Memberships(BaseModel):
    id = IntegerField(primary_key=True)
    user_id = IntegerField()
    token = CharField()
    email = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
