import datetime
import secrets
import string
from typing import Any, Tuple

from app.extensions import db
from app.models import Invitation, Library, MediaServer

CODESIZE = 10
CODESET = string.ascii_uppercase + string.digits


def _generate_code() -> str:
    return "".join(secrets.choice(CODESET) for _ in range(CODESIZE))


def is_invite_valid(code: str) -> Tuple[bool, str]:
    # Try to load the Invitation by code (case-insensitive)
    invitation = Invitation.query.filter(
        db.func.lower(Invitation.code) == code.lower()  # case insensitive
    ).first()
    if not invitation:
        return False, "Invalid code"
    now = datetime.datetime.now()
    if invitation.expires and invitation.expires <= now:
        return False, "Invitation has expired."
    if invitation.used is True and invitation.unlimited is not True:
        return False, "Invitation has already been used."
    return True, "okay"


def create_invite(form: Any) -> Invitation:
    """Takes a WTForms or dict-like `form` with the same keys as your old version."""
    # generate or validate provided code
    code = (form.get("code") or _generate_code()).upper()
    if len(code) != CODESIZE or Invitation.query.filter_by(code=code).first():
        raise ValueError("Invalid or duplicate code")

    now = datetime.datetime.now()
    expires_lookup = {
        "day": now + datetime.timedelta(days=1),
        "week": now + datetime.timedelta(days=7),
        "month": now + datetime.timedelta(days=30),
        "never": None,
    }

    # lookup server id from form or default first
    server_id = form.get("server_id") or None
    if server_id:
        server = MediaServer.query.get(int(server_id))
    else:
        server = MediaServer.query.first()

    invite = Invitation(
        code=code,
        used=False,
        used_at=None,
        created=now,
        expires=expires_lookup.get(form.get("expires")),
        unlimited=bool(form.get("unlimited")),
        duration=form.get("duration") or None,
        # no more comma‐string here:
        plex_allow_sync=bool(form.get("allowsync")),
        plex_home=bool(form.get("plex_home")),
        plex_allow_channels=bool(form.get("plex_allow_channels")),
        server=server,
    )
    db.session.add(invite)
    db.session.flush()  # so invite.id exists, but not yet committed

    # === NEW: wire up the many-to-many ===
    selected = form.getlist("libraries")  # these are your external_ids
    if selected:
        # look up the Library objects
        libs = Library.query.filter(Library.external_id.in_(selected)).all()
        invite.libraries = libs
    # if `selected` is empty, we simply leave invite.libraries = []

    db.session.commit()
    return invite
