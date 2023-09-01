from peewee import SQL, CharField, DateTimeField, ForeignKeyField

from app.models.database.base import BaseModel
from app.models.database.users import Users


class Sessions(BaseModel):
    session = CharField(unique=True)
    user = ForeignKeyField(Users, backref='sessions', on_delete='CASCADE')
    user_agent = CharField()
    ip = CharField()
    expires = DateTimeField(null=True, default=None)
    mfa_id = CharField(null=True, default=None)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
