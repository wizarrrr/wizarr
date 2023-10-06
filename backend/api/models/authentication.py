from app.extensions import api
from flask_restx import fields

LoginPOST = api.model("LoginPOST", {
    "username": fields.String(required=True, description="The account's username"),
    "password": fields.String(required=True, description="The account's password"),
    "remember": fields.Boolean(required=False, description="Keep JWT valid indefinitely", default=False)
})
