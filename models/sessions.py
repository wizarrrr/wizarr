from peewee import SQL, CharField, DateTimeField, ForeignKeyField
from pydantic import BaseModel as PydanticBaseModel

from .base import BaseModel
from .users import Users


class Sessions(BaseModel):
    session = CharField(unique=True)
    user = ForeignKeyField(Users, backref='sessions', on_delete='CASCADE')
    user_agent = CharField()
    ip = CharField()
    expires = DateTimeField(null=True, default=None)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
    
class SessionsModel(PydanticBaseModel):
    session: str
    user: int
    user_agent: str
    ip: str
    expires: str
    created: str