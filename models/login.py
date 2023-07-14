from typing import Optional

from flask_restx import Model, fields
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field


class LoginModel(PydanticBaseModel):
    username: str = Field(description="Username", min_length=3, max_length=30)
    password: str = Field(description="Password", min_length=3, max_length=30)
    remember: Optional[bool] = Field(default=False, description="Remember me")

LoginPostModel = Model("LoginPostModel", {
    "username": fields.String(required=True, description="Username"),
    "password": fields.String(required=True, description="Password"),
    "remember": fields.Boolean(required=False, description="Remember me", default=False)
})