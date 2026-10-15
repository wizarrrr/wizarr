"""Admin changes to the e-mail address that Wizarr keeps for a user."""

from typing import cast

from app.models import Identity, User
from app.services.media.client_base import EMAIL_RE

# Jellyfin and Emby have no e-mail field, so only Wizarr keeps the address of
# their users. The other servers keep their own address and their user sync
# writes it back into Wizarr. Plex also uses the address to find the user.
_WIZARR_EMAIL_SERVER_TYPES = frozenset({"jellyfin", "emby"})

# Values that the user import stores when a server gives no address.
_PLACEHOLDER_EMAILS = frozenset({"", "empty", "None"})


class InvalidEmailError(ValueError):
    """The address does not match the shared e-mail pattern."""


def wizarr_keeps_email(account: User) -> bool:
    """Return True when only Wizarr stores the e-mail of this account."""
    server = account.server
    return server is None or server.server_type in _WIZARR_EMAIL_SERVER_TYPES


def editable_email_accounts(user: User) -> list[User]:
    """Return the accounts of this person whose e-mail the admin can change."""
    accounts = user.identity.accounts if user.identity else [user]
    return [account for account in accounts if wizarr_keeps_email(account)]


def current_email(user: User) -> str:
    """Return the address to show in the edit form, or "" when there is none."""
    for account in editable_email_accounts(user):
        if (account.email or "") not in _PLACEHOLDER_EMAILS:
            return account.email
    return ""


def set_user_email(user: User, raw_email: str) -> None:
    """Store one address on all accounts of this person that Wizarr keeps.

    An empty value removes the address. The media server does not get the
    address. The caller commits the session.
    """
    email = raw_email.strip()
    if email and not EMAIL_RE.fullmatch(email):
        raise InvalidEmailError(email)

    for account in editable_email_accounts(user):
        account.email = email or None
    identity = cast("Identity | None", user.identity)
    if identity:
        identity.primary_email = email or _first_valid_email(identity)


def _first_valid_email(identity: Identity) -> str | None:
    """Return the first real address that an account of the identity has."""
    for account in identity.accounts:
        if account.email and EMAIL_RE.fullmatch(account.email):
            return account.email
    return None
