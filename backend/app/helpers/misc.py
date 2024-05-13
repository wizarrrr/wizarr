from exceptions import WeakPassword
from zxcvbn import zxcvbn


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
