from peewee import SQL, CharField, DateTimeField, ForeignKeyField, IntegerField
from pydantic import BaseModel as PydanticBaseModel

from .base import BaseModel
from .users import Users


class APIKeys(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    key = CharField()
    user = ForeignKeyField(Users, backref='api_keys', on_delete='CASCADE')
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
    expires = DateTimeField(null=True)
    valid = IntegerField(default=1)

class APIKeysModel(PydanticBaseModel):
    id: int
    name: str
    key: str
    user: int
    created: str
    expires: str
    valid: int