from peewee import CharField
from .base import BaseModel

class Settings(BaseModel):
    key = CharField()
    value = CharField(null=True)
    