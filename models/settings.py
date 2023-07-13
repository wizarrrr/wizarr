from peewee import CharField
from pydantic import BaseModel as PydanticBaseModel

from .base import BaseModel


class Settings(BaseModel):
    key = CharField()
    value = CharField(null=True)
    
class SettingsModel(PydanticBaseModel):
    key: str
    value: str