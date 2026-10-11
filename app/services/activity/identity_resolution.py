"""
Utilities for resolving Wizarr users and identities for activity sessions.
"""

from __future__ import annotations

import threading
import time

from sqlalchemy import event, func
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session, joinedload

try:
    from app.extensions import db  # type: ignore
except ImportError:  # pragma: no cover
    db = None  # type: ignore

try:
    from app.models import Identity, User
except ImportError:  # pragma: no cover - during testing without app context
    Identity = None  # type: ignore
    User = None  # type: ignore


# Each poll sends the same user names again. Keep each result for a short time
# so that ingestion and imports do not query the user table for each event.
# The cache also keeps "no match" results, for example for the server owner.
#
# A commit that adds, deletes or renames a User or an Identity clears the cache
# of this process (see the session events below). Other processes see the
# change after IDENTITY_CACHE_TTL_SECONDS.
IDENTITY_CACHE_TTL_SECONDS = 300.0
IDENTITY_CACHE_MAX_ENTRIES = 2048

_identity_cache: dict[
    tuple[int, str], tuple[float, tuple[int | None, int | None, str | None]]
] = {}
_identity_cache_lock = threading.Lock()
# Each clear increments this number. A lookup that started before a clear
# does not store its result, because the result can be old.
_identity_cache_generation = 0

_CHANGED_FLAG = "wizarr_identity_changed"
# The columns that the lookup reads. A change in other columns (for example
# the expiry date) does not change a cached result.
_USER_LOOKUP_COLUMNS = ("username", "server_id", "identity_id")
_IDENTITY_LOOKUP_COLUMNS = ("nickname", "primary_username")


def clear_identity_cache() -> None:
    """Remove all cached identity results."""
    global _identity_cache_generation
    with _identity_cache_lock:
        _identity_cache.clear()
        _identity_cache_generation += 1


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


def _find_matching_user(server_id: int, normalised_name: str) -> User | None:
    """Return the Wizarr user that matches a media server user name."""
    query = (
        db.session.query(User)
        .filter(User.server_id == server_id)
        .options(joinedload(User.identity))  # type: ignore
    )

    # This filter matches the ix_user_server_lower_username index.
    match = (
        query.filter(func.lower(User.username) == normalised_name)
        .order_by(User.id.asc())
        .first()
    )

    if not match:
        match = (
            query.join(Identity, User.identity, isouter=True)  # type: ignore
            .filter(func.lower(Identity.nickname) == normalised_name)
            .order_by(User.id.asc())
            .first()
        )

    if not match:
        match = (
            query.join(Identity, User.identity, isouter=True)  # type: ignore
            .filter(func.lower(Identity.primary_username) == normalised_name)
            .order_by(User.id.asc())
            .first()
        )

    return match


def _lookup(
    server_id: int, normalised_name: str
) -> tuple[int | None, int | None, str | None]:
    """Return (user_id, identity_id, matched display name) from the database."""
    match = _find_matching_user(server_id, normalised_name)
    if not match:
        return None, None, None

    identity_id = match.identity_id if match.identity_id else None
    display_name = _identity_display_name(match.identity, match.username)  # type: ignore
    return match.id, identity_id, display_name


def resolve_user_identity(
    server_id: int,
    _external_user_id: str | None,
    external_user_name: str | None,
) -> tuple[int | None, int | None, str | None]:
    """
    Resolve an activity event user to a Wizarr user and identity.

    Returns a tuple of (wizarr_user_id, wizarr_identity_id, display_name).
    This function always queries the database.
    """
    if db is None or User is None or Identity is None or server_id is None:
        return None, None, external_user_name

    normalised_name = _normalise(external_user_name)
    if not normalised_name:
        return None, None, external_user_name

    user_id, identity_id, display_name = _lookup(server_id, normalised_name)
    return user_id, identity_id, display_name or external_user_name


def resolve_user_identity_cached(
    server_id: int,
    external_user_name: str | None,
) -> tuple[int | None, int | None, str | None]:
    """
    Resolve a user like ``resolve_user_identity`` and keep the result in memory.

    The cache key is (server_id, lower-case user name). The cache also keeps
    "no match" results.
    """
    if db is None or User is None or Identity is None or server_id is None:
        return None, None, external_user_name

    normalised_name = _normalise(external_user_name)
    if not normalised_name:
        return None, None, external_user_name

    key = (server_id, normalised_name)
    now = time.monotonic()

    with _identity_cache_lock:
        cached = _identity_cache.get(key)
        generation = _identity_cache_generation
    if cached is not None and cached[0] > now:
        user_id, identity_id, display_name = cached[1]
        return user_id, identity_id, display_name or external_user_name

    result = _lookup(server_id, normalised_name)

    with _identity_cache_lock:
        # Do not store a result that a commit made old during the lookup.
        if generation == _identity_cache_generation:
            if len(_identity_cache) >= IDENTITY_CACHE_MAX_ENTRIES:
                _identity_cache.clear()
            _identity_cache[key] = (now + IDENTITY_CACHE_TTL_SECONDS, result)

    user_id, identity_id, display_name = result
    return user_id, identity_id, display_name or external_user_name


def apply_identity_resolution(session) -> bool:
    """
    Resolve and attach Wizarr identity details to an ActivitySession.

    Returns True if the session was modified. The result comes from the
    identity cache when possible.
    """
    from app.models import ActivitySession  # local import to avoid circular

    if not isinstance(session, ActivitySession):
        return False

    user_id, identity_id, display_name = resolve_user_identity_cached(
        session.server_id,
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


# ----------------------------------------------------------------------
# Cache invalidation
# ----------------------------------------------------------------------
def _changes_lookup(obj) -> bool:
    """Return True when a flushed object can change an identity lookup."""
    if User is not None and isinstance(obj, User):
        columns = _USER_LOOKUP_COLUMNS
    elif Identity is not None and isinstance(obj, Identity):
        columns = _IDENTITY_LOOKUP_COLUMNS
    else:
        return False
    attrs = sa_inspect(obj).attrs
    return any(attrs[column].history.has_changes() for column in columns)


@event.listens_for(Session, "after_flush")
def _mark_identity_flush(session, _flush_context):
    if User is None or Identity is None:
        return
    for obj in (*session.new, *session.deleted):
        if isinstance(obj, (User, Identity)):
            session.info[_CHANGED_FLAG] = True
            return
    if any(_changes_lookup(obj) for obj in session.dirty):
        session.info[_CHANGED_FLAG] = True


@event.listens_for(Session, "do_orm_execute")
def _mark_identity_bulk_change(orm_execute_state):
    if not (
        orm_execute_state.is_insert
        or orm_execute_state.is_update
        or orm_execute_state.is_delete
    ):
        return
    mapper = orm_execute_state.bind_mapper
    if mapper is not None and mapper.class_ in (User, Identity):
        orm_execute_state.session.info[_CHANGED_FLAG] = True


# The flag stays after a rollback. Then the next commit clears the cache one
# time more than necessary, which is safe.
@event.listens_for(Session, "after_commit")
def _clear_identity_cache_after_commit(session):
    if session.info.pop(_CHANGED_FLAG, False):
        clear_identity_cache()
