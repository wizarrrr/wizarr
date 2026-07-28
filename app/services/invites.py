import datetime
import logging
import secrets
import string
from typing import Any

from sqlalchemy import and_  # type: ignore

from app.extensions import db
from app.models import (
    Invitation,
    Library,
    MediaServer,
    User,
    invitation_servers,
    invitation_users,
)

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
    now = datetime.datetime.now(datetime.UTC)
    # Make database datetime timezone-aware (assumes UTC) for comparison
    if invitation.expires:
        expires_aware = invitation.expires.replace(tzinfo=datetime.UTC)
        if expires_aware <= now:
            return False, "Invitation has expired."
    if invitation.used is True and invitation.unlimited is not True:
        return False, "Invitation has already been used."
    return True, "okay"


def _get_form_list(form: Any, key: str) -> list[str]:
    """Get list from form, handling both WTForms and dict."""
    if hasattr(form, "getlist"):
        # WTForms object
        return form.getlist(key) or []
    # Regular dict
    value = form.get(key, [])
    if isinstance(value, list):
        return value
    if value:
        return [str(value)]
    return []


def create_invite(form: Any) -> Invitation:
    """Takes a WTForms or dict-like `form` with the same keys as your old version."""
    # generate or validate provided code
    code = (form.get("code") or _generate_code()).strip().upper()

    if (
        not (MIN_CODESIZE <= len(code) <= MAX_CODESIZE)
        or Invitation.query.filter_by(code=code).first()
    ):
        raise ValueError("Invalid or duplicate code")

    now = datetime.datetime.now(datetime.UTC)
    expires_lookup = {
        "day": now + datetime.timedelta(days=1),
        "week": now + datetime.timedelta(days=7),
        "month": now + datetime.timedelta(days=30),
        "never": None,
    }

    # ── servers ────────────────────────────────────────────────────────────
    # Get selected server IDs from checkboxes
    server_ids = _get_form_list(form, "server_ids")

    if not server_ids:
        # No servers selected - this is now an error condition
        raise ValueError("At least one server must be selected")

    servers = MediaServer.query.filter(MediaServer.id.in_(server_ids)).all()

    # Sort servers to ensure Plex servers come first for mixed invitations
    plex_servers = [s for s in servers if s.server_type == "plex"]
    other_servers = [s for s in servers if s.server_type != "plex"]
    servers = plex_servers + other_servers

    # Validate the library selection before creating anything. The invite picker
    # (server_library_picker.html) emits a hidden `library_picker_used` marker; if
    # it is present but no box is checked, the admin opened the picker and cleared
    # it. That is almost always a mistake rather than a request for an invite that
    # grants nothing (which the media backends cannot represent anyway), so reject
    # it and point them at the permissive default. When the picker was never opened
    # there is no marker and the redeem-time fallback still grants all enabled
    # libraries, so unattended invites are unaffected.
    #
    # The submitted IDs are validated by resolving them against Library rows that
    # actually belong to one of the selected servers, not by their raw presence:
    # a stale or nonexistent ID would otherwise pass this check while resolving
    # to zero libraries below, committing an unscoped invite that the picker
    # appeared to have restricted.
    selected_library_ids = [
        int(lid) for lid in _get_form_list(form, "libraries") if str(lid).isdigit()
    ]
    resolved_libraries = (
        Library.query.filter(
            Library.id.in_(selected_library_ids),
            Library.server_id.in_([s.id for s in servers]),
        ).all()
        if selected_library_ids
        else []
    )
    if form.get("library_picker_used") and not resolved_libraries:
        raise ValueError(
            "Select at least one library, or leave the library selector "
            "untouched to grant access to all enabled libraries."
        )

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
        wizard_bundle_id=(
            int(form.get("wizard_bundle_id")) if form.get("wizard_bundle_id") else None
        ),
        # Universal flags for all servers
        allow_downloads=bool(
            form.get("allow_downloads")
            or form.get("allowsync")
            or form.get("audiobookshelf_allow_downloads")
        ),
        allow_live_tv=bool(
            form.get("allow_live_tv") or form.get("plex_allow_channels")
        ),
        allow_mobile_uploads=bool(form.get("allow_mobile_uploads")),
        # Jellyfin-specific options
        max_active_sessions=(
            int(form.get("max_active_sessions").strip())
            if form.get("max_active_sessions")
            and str(form.get("max_active_sessions")).strip().isdigit()
            else None
        ),
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

    # Wire up library associations (resolved_libraries computed and validated above)
    if resolved_libraries:
        # Clear any existing library associations for this invite to avoid UNIQUE constraint violations
        # This handles cases where there might be leftover data from previous attempts
        from app.models import invite_libraries

        db.session.execute(
            invite_libraries.delete().where(invite_libraries.c.invite_id == invite.id)
        )
        db.session.flush()  # Ensure the delete is committed before adding new records

        # Since we're now using unique library IDs from the frontend,
        # we shouldn't have duplicates, but we'll keep the deduplication
        # logic as a safety measure
        seen_lib_ids = set()
        for lib in resolved_libraries:
            if lib.id not in seen_lib_ids:
                seen_lib_ids.add(lib.id)
                invite.libraries.append(lib)

    # Wire up LDAP user creation flag
    invite.create_ldap_user = bool(form.get("create_ldap_user"))

    db.session.commit()
    return invite


# ─── Multi-server helpers ───────────────────────────────────────────────────


def mark_server_used(
    inv: Invitation, server_id: int, user: "User | None" = None
) -> None:
    """Mark the invitation as used for a specific server.

    When all attached servers are used we also flip the legacy `inv.used` flag
    so older paths continue to see the invite as consumed.

    This function automatically infers the user association from the invitation's
    used_by field or by finding a user with matching invitation code and server.

    After marking as used, it syncs users from the media server to ensure the
    newly created user appears in the users list.
    """
    db.session.execute(
        invitation_servers.update()
        .where(
            and_(
                invitation_servers.c.invite_id == inv.id,
                invitation_servers.c.server_id == server_id,
            )
        )
        .values(used=True, used_at=datetime.datetime.now(datetime.UTC))
    )

    # Check if *all* servers are now used (only for limited invitations)
    row = db.session.execute(
        invitation_servers.select().where(invitation_servers.c.invite_id == inv.id)
    ).all()
    if row and all(r.used for r in row) and not inv.unlimited:  # type: ignore
        # For limited invitations, mark as fully used when all servers are used
        # For unlimited invitations, this should already be True from the first usage
        inv.used = True
        inv.used_at = datetime.datetime.now(datetime.UTC)

    # Find or use the provided user who used this invitation on this server
    from app.models import User

    if not user:
        # No user provided, try to find by invitation code and server
        # Debug: List all users for this server and invitation code
        all_users = User.query.filter_by(server_id=server_id).all()
        users_with_code = User.query.filter_by(code=inv.code).all()
        logging.info(
            f"Debug: Server {server_id} has {len(all_users)} total users, "
            f"{len(users_with_code)} users with code '{inv.code}'"
        )
        for u in users_with_code:
            logging.info(
                f"  User with code '{inv.code}': {u.username} (server_id={u.server_id})"
            )

        user = User.query.filter_by(code=inv.code, server_id=server_id).first()
    else:
        logging.info(
            f"Using provided user {user.username} for invitation {inv.code} on server {server_id}"
        )

    if user:
        # Add this user to the invitation's users if not already present
        # This handles the many-to-many relationship properly
        existing_usage = db.session.execute(
            invitation_users.select().where(
                and_(
                    invitation_users.c.invite_id == inv.id,
                    invitation_users.c.user_id == user.id,
                )
            )
        ).first()

        if not existing_usage:
            # Record this user's usage of the invitation
            db.session.execute(
                invitation_users.insert().values(
                    invite_id=inv.id,
                    user_id=user.id,
                    used_at=datetime.datetime.now(datetime.UTC),
                    server_id=server_id,
                )
            )
            logging.info(
                f"Successfully recorded usage of invitation {inv.code} by user {user.username} on server {server_id}"
            )

        # Maintain backward compatibility: set used_by_id to the first user if not set
        if not inv.used_by_id:
            inv.used_by_id = user.id
            inv.used_by = user
    else:
        # User not found even after syncing - this is an issue
        logging.error(
            f"User not found for invitation {inv.code} on server {server_id} even after syncing. "
            f"Available users on this server: {[u.username + f'(code={u.code})' for u in all_users]}. "
            f"The invitation-user relationship cannot be created."
        )

    # For unlimited invitations, mark as used after first usage
    # This allows the invitation to show up correctly in the admin interface
    if inv.unlimited and not inv.used:
        inv.used = True
        inv.used_at = datetime.datetime.now(datetime.UTC)

    db.session.commit()
