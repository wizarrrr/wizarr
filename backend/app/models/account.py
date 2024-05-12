from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AccountModel(BaseModel):
    password_hash: str
    email: str
    created: datetime
    last_login: datetime | None = None
    role: Literal["user"] | Literal["admin"] = "user"
    services: list[str] = []


class AccountUpdateModel(BaseModel):
    email: str | None = None
