from peewee import CharField

from models.database.base import BaseModel


class Settings(BaseModel):
    key = CharField()
    value = CharField(null=True)
