"""Choose the primary account of a person and link accounts to one identity."""

from collections.abc import Iterable, Sequence

from app.extensions import db
from app.models import Identity, User
from app.services.media.client_base import EMAIL_RE


def _has_valid_email(user: User) -> bool:
    return bool(EMAIL_RE.fullmatch((user.email or "").strip()))


def primary_account(users: Iterable[User]) -> User:
    """Return the account that represents a person with linked accounts.

    An account with a valid e-mail address comes first, because some servers
    give a placeholder such as "empty". Then the username and the id decide,
    so the order of the query rows has no effect.
    """
    return min(users, key=lambda u: (not _has_valid_email(u), u.username or "", u.id))


def link_user_accounts(user_ids: Sequence[int | str]) -> bool:
    """Link the accounts to one identity. Return False when no account exists."""
    users = User.query.filter(User.id.in_(user_ids)).all()
    if not users:
        return False
    primary = primary_account(users)
    identity = primary.identity or Identity(
        primary_email=primary.email, primary_username=primary.username
    )
    db.session.add(identity)
    db.session.flush()
    for user in users:
        user.identity = identity
    db.session.commit()
    return True
