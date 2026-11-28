from flask import current_app, session
from flask_babel import gettext as _
from flask_login import login_user

from app.extensions import db
from app.models import AdminAccount, OIDCConfiguration


def _claim_matches(claim_value, allowed_values: set[str]) -> bool:
    """Return True if *claim_value* (a scalar or a list claim) intersects
    *allowed_values*. Values are compared as strings."""
    if claim_value is None:
        return False
    if isinstance(claim_value, list | tuple | set):
        return any(str(v) in allowed_values for v in claim_value)
    return str(claim_value) in allowed_values


def handle_oidc_login(
    config: OIDCConfiguration, userinfo: dict
) -> tuple[bool, str]:
    """Authenticate an already-verified OIDC ``userinfo`` claim set as an
    admin, provisioning an :class:`AdminAccount` on first login.

    ``userinfo`` must already have passed ID-token signature/issuer/
    audience/nonce verification -- that happens in Authlib's
    ``authorize_access_token()`` / ``parse_id_token()`` before this is
    called. This function only handles Wizarr-side authorization
    (is this identity allowed to be an admin?) and account provisioning.
    """
    sub = userinfo.get("sub")
    if not sub:
        current_app.logger.warning("OIDC login rejected: no 'sub' claim in userinfo")
        return False, _("OIDC provider did not return a subject identifier")

    username = (
        userinfo.get(config.username_claim)
        or userinfo.get("preferred_username")
        or userinfo.get("email")
        or sub
    )

    # ── Admin authorization gate ─────────────────────────────────────────
    # If no claim restriction is configured, any successfully authenticated
    # OIDC identity is treated as an admin (the Settings UI warns about
    # this loudly). Otherwise the configured claim must match one of the
    # allowed values -- mirrors LDAP's admin_group_dn gate.
    if config.admin_claim:
        allowed_values = {
            v.strip() for v in (config.admin_claim_values or "").split(",") if v.strip()
        }
        claim_value = userinfo.get(config.admin_claim)
        if not allowed_values or not _claim_matches(claim_value, allowed_values):
            current_app.logger.warning(
                "OIDC login denied for sub=%s: claim '%s'=%r not in %s",
                sub,
                config.admin_claim,
                claim_value,
                allowed_values,
            )
            return False, _("You are not authorized as an administrator")

    # ── Find or provision the admin account ──────────────────────────────
    # Match by external_id first (stable across a username change at the
    # IdP), falling back to username so an existing local/LDAP admin
    # account can be "claimed" by an OIDC identity of the same username.
    admin = AdminAccount.query.filter_by(
        external_id=sub, auth_source="oidc"
    ).first()
    if not admin:
        admin = AdminAccount.query.filter_by(username=username).first()

    if not admin:
        admin = AdminAccount(username=username)
        admin.auth_source = "oidc"
        admin.password_hash = None
        admin.external_id = sub
        db.session.add(admin)
        db.session.commit()
        current_app.logger.info("Created new admin account '%s' via OIDC", username)
    elif admin.external_id != sub:
        admin.external_id = sub
        admin.auth_source = "oidc"
        db.session.commit()

    login_user(admin)
    session.permanent = True

    current_app.logger.info("OIDC admin login successful: %s (sub=%s)", username, sub)
    return True, _("Login successful")
