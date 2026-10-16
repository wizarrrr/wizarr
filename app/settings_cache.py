"""Short in-process cache for the Settings values that each request reads.

The context processor reads ``server_name`` and the onboarding check reads
``admin_username`` on each request, also on HTMX polls. This cache keeps the
values for a short time.

A commit that changes a Settings row clears the cache of this process. Other
processes (more gunicorn workers) see the change after ``TTL_SECONDS``.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from flask import current_app, has_app_context
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models import Settings

TTL_SECONDS = 30.0
CACHE_EXTENSION = "wizarr_settings_cache"
_CHANGED_FLAG = "wizarr_settings_changed"


class SettingsCache:
    """Values with an expiry time, and a generation number for invalidation."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.values: dict[str, tuple[float, str | None]] = {}
        self.generation = 0

    def clear(self) -> None:
        with self.lock:
            self.values.clear()
            self.generation += 1


def _cache() -> SettingsCache:
    app = current_app._get_current_object()  # type: ignore[attr-defined]
    cache = app.extensions.get(CACHE_EXTENSION)
    if cache is None:
        cache = app.extensions.setdefault(CACHE_EXTENSION, SettingsCache())
    return cache


def get_cached_setting(
    key: str,
    loader: Callable[[], str | None],
    *,
    cache_empty: bool = True,
    ttl: float = TTL_SECONDS,
) -> str | None:
    """Return the value of the Settings *key*. Call *loader* on a cache miss.

    With ``cache_empty=False``, the cache keeps only a non-empty value, so a
    check for a missing value always reads the database.
    """
    cache = _cache()
    now = time.monotonic()
    with cache.lock:
        entry = cache.values.get(key)
        if entry is not None and entry[0] > now:
            return entry[1]
        generation = cache.generation

    value = loader()

    if value or cache_empty:
        with cache.lock:
            # Do not store a value that a commit made old during the load.
            if cache.generation == generation:
                cache.values[key] = (now + ttl, value)
    return value


def clear_settings_cache() -> None:
    """Clear the cache of the current app."""
    if has_app_context():
        cache = current_app.extensions.get(CACHE_EXTENSION)
        if cache is not None:
            cache.clear()


@event.listens_for(Session, "after_flush")
def _mark_settings_flush(session, _flush_context):
    changed = (*session.new, *session.dirty, *session.deleted)
    if any(isinstance(obj, Settings) for obj in changed):
        session.info[_CHANGED_FLAG] = True


@event.listens_for(Session, "do_orm_execute")
def _mark_settings_bulk_change(orm_execute_state):
    if not (orm_execute_state.is_update or orm_execute_state.is_delete):
        return
    mapper = orm_execute_state.bind_mapper
    if mapper is not None and mapper.class_ is Settings:
        orm_execute_state.session.info[_CHANGED_FLAG] = True


# The flag stays after a rollback. Then the next commit clears the cache one
# time more than necessary, which is safe.
@event.listens_for(Session, "after_commit")
def _clear_after_commit(session):
    if session.info.pop(_CHANGED_FLAG, False):
        clear_settings_cache()
