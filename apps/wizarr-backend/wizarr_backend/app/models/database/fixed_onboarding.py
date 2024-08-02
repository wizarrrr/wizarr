from peewee import CharField, IntegerField
from app.models.database.base import BaseModel

class FixedOnboarding(BaseModel):
    id = IntegerField(primary_key=True, unique=True)
    value = CharField(null=False)
