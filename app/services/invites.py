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
    # Get selected server IDs from checkboxes
    server_ids = form.getlist("server_ids") or []

    if not server_ids:
        # No servers selected - this is now an error condition
        raise ValueError("At least one server must be selected")

    servers = MediaServer.query.filter(MediaServer.id.in_(server_ids)).all()

    # Sort servers to ensure Plex servers come first for mixed invitations
    plex_servers = [s for s in servers if s.server_type == "plex"]
    other_servers = [s for s in servers if s.server_type != "plex"]
    servers = plex_servers + other_servers

    # Keep legacy `server` column for the FIRST selected server (or None)
    # primary_server = servers[0] if servers else None  # TODO: Re-enable when UNIQUE constraint issue is fixed

    # Fix duplicate assignment of allow_downloads and syntax error (missing parenthesis)
    invite = Invitation(
        code=code,
        used=False,
        used_at=None,
        created=now,
        expires=expires_lookup.get(form.get("expires")),
        unlimited=bool(form.get("unlimited")),
        duration=form.get("duration") or None,
        plex_allow_sync=bool(form.get("allowsync") or form.get("allow_downloads")),
        plex_home=bool(form.get("plex_home")),
        plex_allow_channels=bool(
            form.get("plex_allow_channels") or form.get("allow_live_tv")
        ),
        # server=primary_server,  # TODO: Figure out why this causes UNIQUE constraint violation
        wizard_bundle_id=(
            int(form.get("wizard_bundle_id")) if form.get("wizard_bundle_id") else None
        ),
        # Unified flags for all servers
        allow_downloads=bool(
            form.get("allow_downloads")
            or form.get("allowsync")
            or form.get("audiobookshelf_allow_downloads")
        ),
        allow_live_tv=bool(
            form.get("allow_live_tv") or form.get("plex_allow_channels")
        ),
        allow_mobile_uploads=bool(form.get("allow_mobile_uploads")),
    )
    db.session.add(invite)
    db.session.flush()  # so invite.id exists, but not yet committed

    # Attach the selected servers via the new association table
    if servers:
        # Clear any existing server associations for this invite to avoid UNIQUE constraint violations
        # This handles cases where there might be leftover data from previous attempts
        db.session.execute(
            invitation_servers.delete().where(
                invitation_servers.c.invite_id == invite.id
            )
        )
        db.session.flush()  # Ensure the delete is committed before adding new records

        invite.servers.extend(servers)

    # === NEW: wire up the many-to-many ===
    selected = form.getlist("libraries")  # these are your external_ids
    if selected:
        # Look up the Library objects, but only for the selected servers to avoid orphaned libraries
        server_ids = [s.id for s in servers]
        libs = Library.query.filter(
            Library.external_id.in_(selected), Library.server_id.in_(server_ids)
        ).all()
        invite.libraries.extend(libs)

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
