from peewee import SQL, CharField, DateTimeField, ForeignKeyField, IntegerField

from app.models.database.base import BaseModel
from app.models.database.users import Users

class APIKeys(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    key = CharField()
    user = ForeignKeyField(Users, backref='api_keys', on_delete='CASCADE')
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
    expires = DateTimeField(null=True)
    valid = IntegerField(default=1)
