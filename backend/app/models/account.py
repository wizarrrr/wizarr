from datetime import datetime

from pydantic import BaseModel


class AccountModel(BaseModel):
    password_hash: str
    email: str
    created: datetime
    last_login: datetime | None = None
    services: list[str] = []


class AccountUpdateModel(BaseModel):
    email: str | None = None
