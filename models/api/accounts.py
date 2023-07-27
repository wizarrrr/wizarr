from app.extensions import api
from flask_restx import fields

AccountsGET = api.model("AccountsGET", {
    "id": fields.Integer(required=True, description="The account's ID"),
    "username": fields.String(required=True, description="The account's username"),
    "email": fields.String(required=False, description="The account's email"),
    "last_login": fields.DateTime(required=False, description="The account's last login"),
    "created": fields.DateTime(required=False, description="The date the account was created"),
})

AccountsPOST = api.model("AccountsPOST", {
    "username": fields.String(required=True, description="The account's username"),
    "email": fields.String(required=False, description="The account's email"),
    "password": fields.String(required=True, description="The account's password"),
    "confirm_password": fields.String(required=False, description="The account's password confirmation"),
})
