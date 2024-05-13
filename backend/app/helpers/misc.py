from typing import Tuple

from zxcvbn import zxcvbn

from app.exceptions import InvalidInviteCode, WeakPassword


def check_password(password: str) -> None:
    """Checks if password is secure.

    Args:
        password (str)

    Raises:
        WeakPassword
    """

    zxcvbn_results = zxcvbn(password)
    if zxcvbn_results["score"] < 3:
        raise WeakPassword(feedback=zxcvbn_results["feedback"])


def invite_code_decoded(self) -> Tuple[str, str]:
    try:
        _id, password = self._code.split(":")
    except ValueError:
        raise InvalidInviteCode()

    return _id, password
