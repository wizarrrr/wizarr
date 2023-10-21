from peewee import SQL, CharField, DateTimeField, ForeignKeyField, BooleanField

from app.models.database.base import BaseModel
from app.models.database.users import Users


class Sessions(BaseModel):
    access_jti = CharField(unique=True)
    refresh_jti = CharField(unique=True, null=True, default=None)
    user = ForeignKeyField(Users, backref='sessions', on_delete='CASCADE')
    user_agent = CharField()
    ip = CharField()
    expires = DateTimeField(null=True, default=None)
    mfa_id = CharField(null=True, default=None)
    revoked = BooleanField(default=False)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
