from flask_restx import Model, fields
from peewee import SQL, CharField, DateTimeField, IntegerField
from pydantic import BaseModel as PydanticBaseModel

from .base import BaseModel


class Admins(BaseModel):
    id = IntegerField(primary_key=True)
    username = CharField(unique=True)
    password = CharField()
    email = CharField(null=True, unique=True, default=None)
    last_login = DateTimeField(null=True, default=None)
    created = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])

class AdminsModel(PydanticBaseModel):
    id: int
    username: str
    password: str
    email: str
    last_login: str
    created: str
    

AdminsPostModel = Model('AdminsPostModel', {
    "username": fields.String(required=True, description="Username"),
    "password": fields.String(required=True, description="Password"),
    "email": fields.String(required=False, description="Email"),
})

AdminsGetModel = Model('AdminsGetModel', {
    "id": fields.Integer(required=True, description="The ID of the admin"),
    "username": fields.String(required=True, description="Username"),
    "email": fields.String(required=False, description="Email", allow_null=True),
    "last_login": fields.String(required=False, description="Last login", allow_null=True),
    "created": fields.String(required=False, description="The date the admin was created", allow_null=True),
})