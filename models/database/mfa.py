from peewee import SQL, CharField, DateTimeField, IntegerField
from models.database.base import BaseModel


class MFA(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField(unique=True)
    user_id = CharField()
    credential_id = CharField(unique=True)
    public_key = CharField(unique=True)
    sign_count = IntegerField()
    attestation = CharField(unique=True)
    transports = CharField()
    created_at = DateTimeField(constraints=[SQL("DEFAULT CURRENT_TIMESTAMP")])
