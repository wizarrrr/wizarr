from peewee import BooleanField, CharField, IntegerField
from app.models.database.base import BaseModel

class Onboarding(BaseModel):
    id = IntegerField(primary_key=True, unique=True)
    value = CharField()
    order = IntegerField(null=False, unique=True)
    enabled = BooleanField(default=True)
    template = IntegerField()
    editable = BooleanField(default=True)
