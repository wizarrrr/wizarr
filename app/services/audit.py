"""An audit trail of changes to people's accounts.

Wizarr logs at WARNING by default, so a join, a delete, a disable or a sync that
adds or drops an account left nothing to read afterwards. This writes one line
per change to the ``wizarr.audit`` logger, which has its own handler at INFO,
whatever ``LOG_LEVEL`` is:

    AUDIT user_removed actor=alex id=96 server=Books username=... email=... code=...

Changes are caught where they happen, on the User model, so every path is
covered: the admin pages, the API, the expiry job, a join and the user sync. The
actor is the signed-in admin, the Cloudflare Access email, ``invitee`` for
anyone else making a request, or ``system`` outside a request (the scheduler).
An account the sync imported has the code ``empty``, so it shows ``source=sync``.
"""

import logging
from typing import Any

from flask import g, has_request_context
from flask_login import current_user
from sqlalchemy import event, inspect, select

from app.models import Invitation, MediaServer, User

audit_logger = logging.getLogger("wizarr.audit")

# Columns whose changes are worth a line (a rename or a note is not)
_TRACKED = ("is_disabled", "expires", "server_id", "identity_id")
# What the user sync gives an account it imports
_SYNC_CODES = ("empty", "")


def actor() -> str:
    """Who is making this change."""
    if not has_request_context():
        return "system"
    # Flask-Login keeps the user it finds on g. Reading it here, before the request
    # has signed anyone in, must not leave "anonymous" behind for the rest of it.
    cached = "_login_user" in g
    try:
        if current_user.is_authenticated:
            return str(getattr(current_user, "username", None) or "admin")
    except Exception:
        logging.getLogger(__name__).debug("audit: no signed-in admin", exc_info=True)
    finally:
        if not cached:
            g.pop("_login_user", None)
    try:
        from app.services import cloudflare_access

        claims = (
            cloudflare_access.verified_claims() if cloudflare_access.enabled() else None
        )
        if claims and claims.get("email"):
            return str(claims["email"])
    except Exception:
        logging.getLogger(__name__).debug("audit: no Access claims", exc_info=True)
    return "invitee"


def _value(value: Any) -> str:
    text = str(value)
    return f'"{text}"' if " " in text or not text else text


def audit(name: str, **fields: Any) -> None:
    """Write one audit line. ``None`` fields are left out."""
    # Alembic's env.py runs fileConfig, which disables loggers made before it ran
    audit_logger.disabled = False
    rest = " ".join(f"{k}={_value(v)}" for k, v in fields.items() if v is not None)
    audit_logger.info("AUDIT %s actor=%s %s", name, actor(), rest)


def audit_remote(operation: str, user: User, ok: bool, error: object = None) -> None:
    """One line for a call Wizarr made to a media server about an account."""
    server = getattr(user, "server", None)
    audit(
        f"remote_{operation}",
        id=user.id,
        server=getattr(server, "name", None),
        username=user.username,
        ok=ok,
        error=str(error)[:120] if error else None,
    )


# Server names by id, so an audit line doesn't cost a query for every account (a
# user sync adds or drops many). A rename or a delete of the server clears its entry.
_server_names: dict[int, str | None] = {}


def _server_name(connection, server_id: int | None) -> str | None:
    if server_id is None:
        return None
    if server_id not in _server_names:
        _server_names[server_id] = connection.execute(
            select(MediaServer.name).where(MediaServer.id == server_id)
        ).scalar()
    return _server_names[server_id]


def _forget_server(_mapper, _connection, server: MediaServer) -> None:
    _server_names.pop(server.id, None)


def _user_fields(connection, user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "server": _server_name(connection, user.server_id),
        "username": user.username,
        "email": user.email,
        "code": user.code,
    }


def _on_user_added(_mapper, connection, user: User) -> None:
    try:
        source = "sync" if (user.code or "") in _SYNC_CODES else "invite"
        audit("user_added", source=source, **_user_fields(connection, user))
    except Exception:
        logging.getLogger(__name__).exception("audit: user_added failed")


def _on_user_removed(_mapper, connection, user: User) -> None:
    try:
        audit("user_removed", **_user_fields(connection, user))
    except Exception:
        logging.getLogger(__name__).exception("audit: user_removed failed")


def _on_user_changed(_mapper, connection, user: User) -> None:
    try:
        state = inspect(user)
        for column in _TRACKED:
            history = state.attrs[column].history
            if not history.has_changes():
                continue
            old = history.deleted[0] if history.deleted else None
            new = history.added[0] if history.added else None
            if old == new:
                continue
            audit(
                "user_changed",
                field=column,
                old=old,
                new=new,
                **_user_fields(connection, user),
            )
    except Exception:
        logging.getLogger(__name__).exception("audit: user_changed failed")


def _on_invitation_added(_mapper, _connection, invitation: Invitation) -> None:
    try:
        audit(
            "invite_created",
            code=invitation.code,
            person=getattr(invitation, "invitee_name", None),
            unlimited=bool(invitation.unlimited),
            expires=invitation.expires,
        )
    except Exception:
        logging.getLogger(__name__).exception("audit: invite_created failed")


def _on_invitation_removed(_mapper, _connection, invitation: Invitation) -> None:
    try:
        audit("invite_deleted", code=invitation.code, used=bool(invitation.used))
    except Exception:
        logging.getLogger(__name__).exception("audit: invite_deleted failed")


def register() -> None:
    """Start recording. Safe to call more than once."""
    for target, name, fn in (
        (User, "after_insert", _on_user_added),
        (User, "after_delete", _on_user_removed),
        (User, "after_update", _on_user_changed),
        (Invitation, "after_insert", _on_invitation_added),
        (Invitation, "after_delete", _on_invitation_removed),
        (MediaServer, "after_update", _forget_server),
        (MediaServer, "after_delete", _forget_server),
    ):
        if not event.contains(target, name, fn):
            event.listen(target, name, fn)
