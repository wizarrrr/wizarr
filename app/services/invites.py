import secrets
import string
import datetime
from typing import Tuple, Any
from app.extensions import db
from app.models import Invitation

CODESIZE = 6
CODESET  = string.ascii_uppercase + string.digits

def _generate_code() -> str:
    return ''.join(secrets.choice(CODESET) for _ in range(CODESIZE))

def is_invite_valid(code: str) -> Tuple[bool, str]:
    # Try to load the Invitation by code (case-insensitive)
    invitation = Invitation.query.filter(
        db.func.lower(Invitation.code) == code.lower()
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
    # check length and uniqueness
    if len(code) != CODESIZE or Invitation.query.filter_by(code=code).first():
        raise ValueError("Invalid or duplicate code")

    now = datetime.datetime.now()
    expires_lookup = {
        "day":   now + datetime.timedelta(days=1),
        "week":  now + datetime.timedelta(days=7),
        "month": now + datetime.timedelta(days=30),
        "never": None,
    }

    invite = Invitation(
        code       = code,
        used       = False,
        used_at    = None,
        created    = now,
        expires    = expires_lookup.get(form.get("expires")),
        unlimited  = bool(form.get("unlimited")),
        duration   = form.get("duration") or None,
        specific_libraries = form.get("libraries") or None,
        plex_allow_sync    = bool(form.get("allowsync")),
        plex_home          = bool(form.get("plex_home")),
        used_by            = None,
    )

    db.session.add(invite)
    db.session.commit()
    return invite
