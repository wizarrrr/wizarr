from peewee import SQL, CharField, DateTimeField, IntegerField
from models.database.base import BaseModel

class Accounts(BaseModel):
    id = IntegerField(primary_key=True)
    username = CharField(unique=True)
    password = CharField()
    email = CharField(null=True, unique=True, default=None)
    last_login = DateTimeField(null=True, default=None)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
