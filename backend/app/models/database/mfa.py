from peewee import SQL, CharField, DateTimeField, IntegerField
from app.models.database.base import BaseModel


class MFA(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    user_id = CharField()
    credential_id = CharField(unique=True)
    public_key = CharField(unique=True)
    sign_count = IntegerField()
    attestation = CharField(unique=True)
    transports = CharField()
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
