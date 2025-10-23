"""
Utilities for resolving Wizarr users and identities for activity sessions.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import joinedload

try:
    from app.extensions import db  # type: ignore
except ImportError:  # pragma: no cover
    db = None  # type: ignore

try:
    from app.models import Identity, User
except ImportError:  # pragma: no cover - during testing without app context
    Identity = None  # type: ignore
    User = None  # type: ignore


def _normalise(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value.lower() if value else None


def _identity_display_name(
    identity: Identity | None, fallback: str | None
) -> str | None:
    if identity:
        return identity.nickname or identity.primary_username or fallback
    return fallback


def resolve_user_identity(
    server_id: int,
    _external_user_id: str | None,
    external_user_name: str | None,
) -> tuple[int | None, int | None, str | None]:
    """
    Resolve an activity event user to a Wizarr user and identity.

    Returns a tuple of (wizarr_user_id, wizarr_identity_id, display_name).
    """
    if db is None or User is None or Identity is None or server_id is None:
        return None, None, external_user_name

    query = (
        db.session.query(User)
        .filter(User.server_id == server_id)
        .options(joinedload(User.identity))
    )

    match: User | None = None

    normalised_name = _normalise(external_user_name)

    if normalised_name:
        match = (
            query.filter(func.lower(User.username) == normalised_name)
            .order_by(User.id.asc())
            .first()
        )

    if not match and normalised_name:
        match = (
            query.join(Identity, User.identity, isouter=True)
            .filter(func.lower(Identity.nickname) == normalised_name)
            .order_by(User.id.asc())
            .first()
        )

    if not match and normalised_name:
        match = (
            query.join(Identity, User.identity, isouter=True)
            .filter(func.lower(Identity.primary_username) == normalised_name)
            .order_by(User.id.asc())
            .first()
        )

    display_name = None
    wizarr_user_id = None
    identity_id = None

    if match:
        wizarr_user_id = match.id
        identity_id = match.identity_id if match.identity_id else None
        display_name = _identity_display_name(match.identity, match.username)

    if not display_name:
        display_name = external_user_name

    return wizarr_user_id, identity_id, display_name


def apply_identity_resolution(session) -> bool:
    """
    Resolve and attach Wizarr identity details to an ActivitySession.

    Returns True if the session was modified.
    """
    from app.models import ActivitySession  # local import to avoid circular

    if not isinstance(session, ActivitySession):
        return False

    user_id, identity_id, display_name = resolve_user_identity(
        session.server_id,
        getattr(session, "user_id", None),
        getattr(session, "user_name", None),
    )

    changed = False

    if user_id and session.wizarr_user_id != user_id:
        session.wizarr_user_id = user_id
        changed = True

    if identity_id and session.wizarr_identity_id != identity_id:
        session.wizarr_identity_id = identity_id
        changed = True

    if display_name and session.user_name != display_name:
        session.user_name = display_name
        changed = True

    session._resolved_identity_name = display_name or session.user_name

    return changed
