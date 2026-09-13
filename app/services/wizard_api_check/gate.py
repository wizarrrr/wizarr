"""Server-side state for the wizard API-check gate.

Client-side gating is advisory - a user can edit the DOM or type a later step
URL. This module is the authoritative half: it records which gates an
invitation has satisfied, enforces the re-check cooldown, and tells the wizard
routes how far the user is actually allowed to navigate.

State lives in the Flask session, which is server-side (``SESSION_TYPE =
"cachelib"``), so the browser holds only a signed session id and cannot forge a
pass. The blob is scoped to a hash of the invitation code and is discarded
wholesale the moment that scope changes, so one invitation's pass can never be
replayed against another in the same browser.
"""

import hashlib
import threading
import time
from typing import Any

from flask import session
from flask_login import current_user

GATE_SESSION_KEY = "wizard_api_gates"

# Session writes are read-modify-write, so two concurrent polls could both see a
# stale cooldown. This in-process floor closes that window within a worker; across
# gunicorn workers the residual is at most one extra call per interval per worker.
_CALL_LOCK = threading.Lock()
_IN_PROCESS_CALLS: dict[str, float] = {}
_IN_PROCESS_TTL = 3600


def _scope() -> str:
    """Identify whose gate state this is, without storing the invite code."""
    code = session.get("wizard_access")
    if code:
        return hashlib.sha256(str(code).encode()).hexdigest()[:32]
    if current_user.is_authenticated:
        return f"admin:{getattr(current_user, 'id', '?')}"
    return "anon"


def _state() -> dict[str, Any]:
    """Return this scope's gate state, discarding anything from another scope."""
    scope = _scope()
    blob = session.get(GATE_SESSION_KEY)
    if not isinstance(blob, dict) or blob.get("scope") != scope:
        blob = {"scope": scope, "passed": [], "next_at": {}, "started": {}}
        session[GATE_SESSION_KEY] = blob
    return blob


def _save(blob: dict[str, Any]) -> None:
    session[GATE_SESSION_KEY] = blob
    session.modified = True


def clear() -> None:
    """Forget every gate for this session (wizard completion, invite reset)."""
    session.pop(GATE_SESSION_KEY, None)


def has_passed(step_id: int | None) -> bool:
    if step_id is None:
        return False
    return step_id in _state().get("passed", [])


def mark_passed(step_id: int | None) -> None:
    if step_id is None:
        return
    blob = _state()
    if step_id not in blob["passed"]:
        blob["passed"].append(step_id)
    blob["next_at"].pop(str(step_id), None)
    _save(blob)


def note_poll_started(step_id: int | None) -> None:
    """Record when polling for *step_id* began, so the cap can be applied."""
    if step_id is None:
        return
    blob = _state()
    blob["started"].setdefault(str(step_id), time.time())
    _save(blob)


def is_capped(step_id: int | None, *, max_poll_seconds: int) -> bool:
    """Whether automatic polling has run long enough to give up on its own."""
    if step_id is None:
        return False
    started = _state().get("started", {}).get(str(step_id))
    return bool(started) and (time.time() - started) > max_poll_seconds


def _prune(now: float) -> None:
    for key, seen in list(_IN_PROCESS_CALLS.items()):
        if now - seen > _IN_PROCESS_TTL:
            del _IN_PROCESS_CALLS[key]


def reserve(step_id: int | None, *, interval: int) -> float:
    """Atomically claim the next upstream call slot for *step_id*.

    Returns ``0.0`` when the caller may make the call, otherwise the seconds
    still to wait. The slot is claimed *before* the upstream request so that
    parallel requests cannot each decide they are first.
    """
    if step_id is None:
        return 0.0

    with _CALL_LOCK:
        now = time.time()
        _prune(now)
        key = f"{_scope()}:{step_id}"

        blob = _state()
        session_next = float(blob.get("next_at", {}).get(str(step_id), 0) or 0)
        process_next = _IN_PROCESS_CALLS.get(key, 0.0) + interval
        allowed_at = max(session_next, process_next)

        if now < allowed_at:
            return allowed_at - now

        _IN_PROCESS_CALLS[key] = now
        blob["next_at"][str(step_id)] = now + interval
        blob["started"].setdefault(str(step_id), now)
        _save(blob)
        return 0.0


def first_locked_index(steps: list, *, exempt: bool) -> int | None:
    """Index of the earliest step whose gate is still unsatisfied.

    ``None`` means the user may go anywhere in *steps*. Admins are exempt so
    previewing a wizard never traps them behind their own gate.
    """
    if exempt:
        return None

    passed = set(_state().get("passed", []))
    for index, item in enumerate(steps):
        config = getattr(item, "api_check", None)
        step_id = getattr(item, "step_id", None)
        if (
            config is not None
            and config.is_active
            and step_id is not None
            and step_id not in passed
        ):
            return index
    return None
