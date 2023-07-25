from typing import Optional
from datetime import datetime

class UsersModel:
    token: str
    username: str
    email: Optional[str]
    code: Optional[str]
    expires: datetime
    auth: Optional[str]

    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self):
        model = {}

        for key, value in self.__dict__.items():
            if key != "_state":
                model[key] = value

        return model
