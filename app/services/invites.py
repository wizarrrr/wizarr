import datetime
import secrets
import string
from typing import Any

from sqlalchemy import and_  # type: ignore

from app.extensions import db
from app.models import Invitation, Library, MediaServer, invitation_servers

MIN_CODESIZE = 6  # Minimum allowed invite code length
MAX_CODESIZE = 10  # Maximum allowed invite code length (default for generated codes)
CODESET = string.ascii_uppercase + string.digits

# Backwards-compat alias for existing usages
CODESIZE = MAX_CODESIZE


def _generate_code() -> str:
    """Generate a random invite code using the full *maximum* length (10 characters)."""
    return "".join(secrets.choice(CODESET) for _ in range(MAX_CODESIZE))


def is_invite_valid(code: str) -> tuple[bool, str]:
    # Quick length sanity check before hitting DB
    if not (MIN_CODESIZE <= len(code) <= MAX_CODESIZE):
        return False, "Invalid code length"

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

    if (
        not (MIN_CODESIZE <= len(code) <= MAX_CODESIZE)
        or Invitation.query.filter_by(code=code).first()
    ):
        raise ValueError("Invalid or duplicate code")

    now = datetime.datetime.now()
    expires_lookup = {
        "day": now + datetime.timedelta(days=1),
        "week": now + datetime.timedelta(days=7),
        "month": now + datetime.timedelta(days=30),
        "never": None,
    }

    # ── servers ────────────────────────────────────────────────────────────
    # NEW: allow selecting multiple servers.  Legacy single‐select field
    #       continues to work for backwards compatibility.
    server_ids = form.getlist("server_ids") or []
    if not server_ids and form.get("server_id"):
        server_ids = [form.get("server_id")]

    if not server_ids:
        # Fallback – default to the first configured server (if any)
        default_server = MediaServer.query.first()
        server_ids = [default_server.id] if default_server else []

    servers = MediaServer.query.filter(MediaServer.id.in_(server_ids)).all()

    # Keep legacy `server` column for the FIRST selected server (or None)
    primary_server = servers[0] if servers else None

    invite = Invitation()
    invite.code = code
    invite.used = False
    invite.used_at = None
    invite.created = now
    invite.expires = expires_lookup.get(form.get("expires"))
    invite.unlimited = bool(form.get("unlimited"))
    invite.duration = form.get("duration") or None
    invite.plex_allow_sync = bool(form.get("allowsync"))
    invite.plex_home = bool(form.get("plex_home"))
    invite.plex_allow_channels = bool(form.get("plex_allow_channels"))
    invite.server = primary_server
    invite.wizard_bundle_id = (
        int(form.get("wizard_bundle_id")) if form.get("wizard_bundle_id") else None
    )
    # New Jellyfin flags
    invite.jellyfin_allow_downloads = bool(form.get("jellyfin_allow_downloads"))
    invite.jellyfin_allow_live_tv = bool(form.get("jellyfin_allow_live_tv"))
    # Universal download permission (used by Audiobookshelf and others)
    invite.allow_downloads = bool(form.get("audiobookshelf_allow_downloads"))
    db.session.add(invite)
    db.session.flush()  # so invite.id exists, but not yet committed

    # Attach the selected servers via the new association table
    if servers:
        invite.servers = servers

    # === NEW: wire up the many-to-many ===
    selected = form.getlist("libraries")  # these are your external_ids
    if selected:
        # Look up the Library objects, but only for the selected servers to avoid orphaned libraries
        server_ids = [s.id for s in servers]
        libs = Library.query.filter(
            Library.external_id.in_(selected), Library.server_id.in_(server_ids)
        ).all()
        invite.libraries = libs
    # if `selected` is empty, we simply leave invite.libraries = []

    db.session.commit()
    return invite


# ─── Multi-server helpers ───────────────────────────────────────────────────


def mark_server_used(inv: Invitation, server_id: int) -> None:
    """Mark the invitation as used for a specific server.

    When all attached servers are used we also flip the legacy `inv.used` flag
    so older paths continue to see the invite as consumed.
    """
    db.session.execute(
        invitation_servers.update()
        .where(
            and_(
                invitation_servers.c.invite_id == inv.id,
                invitation_servers.c.server_id == server_id,
            )
        )
        .values(used=True, used_at=datetime.datetime.now())
    )

    # Check if *all* servers are now used
    row = db.session.execute(
        invitation_servers.select().where(invitation_servers.c.invite_id == inv.id)
    ).all()
    if row and all(r.used for r in row):  # type: ignore[attr-defined]
        inv.used = True
        inv.used_at = datetime.datetime.now()

    db.session.commit()
