from peewee import SQL, CharField, DateTimeField, IntegerField
from app.models.database.base import BaseModel


class OAuthClients(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField(null=True, default=None)
    issuer = CharField(unique=True)
    consumer_key = CharField(null=True, default=None)
    consumer_secret = CharField(null=True, default=None)
    request_token_params = CharField(null=True, default=None)
    request_token_url = CharField(null=True, default=None)
    access_token_method = CharField(null=True, default=None)
    access_token_url = CharField(null=True, default=None)
    authorize_url = CharField(null=True, default=None)
    userinfo_endpoint = CharField(null=True, default=None)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
