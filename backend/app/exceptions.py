from typing import Any

import zxcvbn
from litestar.exceptions import ClientException, NotFoundException


class EmailTaken(ClientException):
    def __init__(
        self,
        *args: Any,
        detail: str = "Username taken",
    ) -> None:
        super().__init__(*args, detail=detail)


class ServiceIdTaken(ClientException):
    def __init__(
        self,
        *args: Any,
        detail: str = "Service Id taken",
    ) -> None:
        super().__init__(*args, detail=detail)


class AccountNotFound(NotFoundException):
    def __init__(
        self,
        *args: Any,
        detail: str = "Account not found",
    ) -> None:
        super().__init__(*args, detail=detail)


class WeakPassword(ClientException):

    def __init__(
        self,
        *args: Any,
        detail: str = "Password is too weak",
        feedback: zxcvbn.feedback._Feedback,
    ) -> None:
        super().__init__(*args, detail=detail, extra={"feedback": feedback})
