from peewee import SQL, CharField, DateTimeField, IntegerField

from app.models.database.base import BaseModel
from app.models.database.users import Users

class APIKeys(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    key = CharField()
    jti = CharField()
    user_id = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
