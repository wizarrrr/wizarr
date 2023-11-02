from peewee import SQL, BooleanField, CharField, DateTimeField
from app.models.database.base import BaseModel


class Discord(BaseModel):
    token = CharField(null=True, default=None)
    enabled = BooleanField(default=False)
    guild_id = CharField(null=True, default=None)
