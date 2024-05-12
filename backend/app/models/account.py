from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AccountModel(BaseModel):
    username: str
    password: str
    email: str
    created: datetime
    last_login: datetime
    role: Literal["user"] | Literal["admin"] = "user"
