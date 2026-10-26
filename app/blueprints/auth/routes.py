import logging
import os

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_babel import _
from flask_login import login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from app.extensions import db, limiter
from app.models import AdminAccount, AdminUser, Settings
from app.services import cloudflare_access

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    # Cloudflare Access mode takes precedence over every other login method,
    # including DISABLE_BUILTIN_AUTH: no valid Access token, no admin session.
    if cloudflare_access.enabled():
        claims = cloudflare_access.verified_claims()
        if claims is None:
            return (
                _("Sign in through Cloudflare Access to reach the admin pages."),
                403,
            )
        logging.info(
            "Admin login via Cloudflare Access: %s",
            claims.get("email") or claims.get("common_name") or "unknown",
        )
        login_user(AdminUser())
        return redirect("/")

    if os.getenv("DISABLE_BUILTIN_AUTH", "").lower() == "true":
        login_user(AdminUser(), remember=bool(request.form.get("remember")))
        return redirect("/")

    # Pre-compute shared template context
    from app.models import LDAPConfiguration, OIDCConfiguration, WebAuthnCredential

    has_passkeys = WebAuthnCredential.query.first() is not None
    ldap_config = LDAPConfiguration.query.first()
    ldap_enabled = bool(
        ldap_config and ldap_config.enabled and ldap_config.allow_admin_bind
    )
    oidc_config = OIDCConfiguration.query.first()
    oidc_enabled = bool(oidc_config and oidc_config.enabled)
    oidc_provider_name = oidc_config.display_name if oidc_config else None
    media_server_url = request.cookies.get("wizarr_media_server_url")

    if request.method in ("GET", "HEAD"):
        return render_template(
            "login.html",
            has_passkeys=has_passkeys,
            ldap_enabled=ldap_enabled,
            oidc_enabled=oidc_enabled,
            oidc_provider_name=oidc_provider_name,
            media_server_url=media_server_url,
            error=request.args.get("error"),
        )

    username = request.form.get("username")
    password = request.form.get("password")
    auth_method = request.form.get("auth_method", "local")

    # ── Handle LDAP authentication ─────────────────────────────────────
    if auth_method == "ldap":
        from .ldap_auth import handle_ldap_login

        success, message = handle_ldap_login(username, password)
        if success:
            return redirect("/")

        return render_template(
            "login.html",
            error=message,
            has_passkeys=has_passkeys,
            ldap_enabled=ldap_enabled,
            oidc_enabled=oidc_enabled,
            oidc_provider_name=oidc_provider_name,
            media_server_url=media_server_url,
            selected_auth_method=auth_method,
        )

    # ── 1) Multi-admin accounts (preferred) ────────────────────────────
    if (
        account := AdminAccount.query.filter_by(username=username).first()
    ) and account.check_password(password):
        # Check if this account has passkeys registered - if so, require 2FA
        from app.models import WebAuthnCredential

        if WebAuthnCredential.query.filter_by(admin_account_id=account.id).first():
            # Store user in session for 2FA verification
            from flask import session

            session["pending_2fa_user_id"] = account.id
            session["pending_2fa_remember"] = bool(request.form.get("remember"))
            return render_template(
                "login.html", show_2fa=True, username=username, has_passkeys=True
            )
        # No passkeys, allow direct login
        login_user(account, remember=bool(request.form.get("remember")))
        return redirect("/")

    # fetch the stored admin credentials
    admin_username = (
        db.session.query(Settings.value).filter_by(key="admin_username").scalar()
    )
    admin_password_hash = (
        db.session.query(Settings.value).filter_by(key="admin_password").scalar()
    )

    if (
        username == admin_username
        and password
        and check_password_hash(admin_password_hash, password)
    ):
        # Legacy single-admin (Settings table)
        login_user(AdminUser(), remember=bool(request.form.get("remember")))
        return redirect("/")

    # Get IP address: prefer Cloudflare's header, then X-Forwarded-For, then remote_addr
    client_ip = (
        request.headers.get("CF-Connecting-IP")
        or (request.headers.get("X-Forwarded-For") or request.remote_addr or "")
        .split(",")[0]
        .strip()
    )

    # Log failed login with IP
    logging.warning(f"AUTH FAIL: Failed login for user '{username}' from {client_ip}")

    return render_template(
        "login.html",
        error=_("Invalid username or password"),
        has_passkeys=has_passkeys,
        ldap_enabled=ldap_enabled,
        oidc_enabled=oidc_enabled,
        oidc_provider_name=oidc_provider_name,
        media_server_url=media_server_url,
        selected_auth_method=auth_method,
    )


@auth_bp.route("/complete-2fa", methods=["POST"])
@limiter.limit("10 per minute")
def complete_2fa():
    """Complete 2FA authentication with passkey."""
    from flask import session

    user_id = session.get("pending_2fa_user_id")
    remember = session.get("pending_2fa_remember", False)

    if not user_id:
        # Check if there are any passkeys registered for error page
        from app.models import WebAuthnCredential

        has_passkeys = WebAuthnCredential.query.first() is not None
        return render_template(
            "login.html",
            error=_("No pending 2FA authentication"),
            has_passkeys=has_passkeys,
        )

    # Get the user account
    account = db.session.get(AdminAccount, user_id)
    if not account:
        session.pop("pending_2fa_user_id", None)
        session.pop("pending_2fa_remember", None)
        # Check if there are any passkeys registered for error page
        from app.models import WebAuthnCredential

        has_passkeys = WebAuthnCredential.query.first() is not None
        return render_template(
            "login.html", error=_("Authentication failed"), has_passkeys=has_passkeys
        )

    # The actual WebAuthn verification will be handled by the existing WebAuthn route
    # This route is called after successful WebAuthn authentication
    session.pop("pending_2fa_user_id", None)
    session.pop("pending_2fa_remember", None)

    login_user(account, remember=remember)
    return redirect("/")


# ── OIDC (admin panel SSO) ───────────────────────────────────────────────
# These two routes must remain reachable without an existing Wizarr session
# -- same requirement as /login itself. If Wizarr is run behind a
# forward-auth reverse proxy with DISABLE_BUILTIN_AUTH set, these routes are
# unused (the proxy handles auth before requests reach Wizarr at all).


@auth_bp.route("/oidc/login", methods=["GET"])
@limiter.limit("10 per minute")
def oidc_login():
    """Kick off the OIDC Authorization Code (+ PKCE) flow."""
    from app.services.oidc.client import get_oidc_client

    client = get_oidc_client()
    if not client:
        return redirect(
            url_for("auth.login", error=_("OIDC sign-in is not configured"))
        )

    # Deliberately built from the *current* request (url_for(..., _external=True)
    # uses request.url_root when SERVER_NAME isn't set), not a single fixed
    # instance URL. This lets Wizarr be reached at more than one hostname
    # (LAN address, public domain, ...) as long as each callback URL is
    # registered as a valid redirect URI on the IdP -- Authentik, Keycloak,
    # Auth0, Okta and Azure AD all support registering more than one.
    redirect_uri = url_for("auth.oidc_callback", _external=True)
    return client.authorize_redirect(redirect_uri)


@auth_bp.route("/oidc/callback", methods=["GET"])
@limiter.limit("10 per minute")
def oidc_callback():
    """OIDC callback: exchange the code, verify the ID token, log in."""
    from app.services.oidc.client import get_oidc_client, get_oidc_config

    from .oidc_auth import handle_oidc_login

    config = get_oidc_config()
    client = get_oidc_client(config)
    if not client:
        return redirect(
            url_for("auth.login", error=_("OIDC sign-in is not configured"))
        )

    try:
        # Validates `state` (CSRF), exchanges the code, and -- because the
        # client was registered with server_metadata_url and an "openid"
        # scope -- verifies the ID token (issuer, audience, expiry, nonce)
        # and returns the verified claims as token["userinfo"].
        token = client.authorize_access_token()
    except Exception:
        current_app.logger.warning(
            "OIDC callback: token exchange/verification failed", exc_info=True
        )
        return redirect(url_for("auth.login", error=_("OIDC sign-in failed")))

    userinfo = token.get("userinfo")
    if not userinfo:
        # Uncommon for a spec-compliant provider, but fall back to the
        # userinfo endpoint if the token response didn't include claims.
        try:
            userinfo = client.userinfo(token=token)
        except Exception:
            current_app.logger.warning(
                "OIDC callback: no userinfo in token and userinfo endpoint failed",
                exc_info=True,
            )
            userinfo = None

    if not userinfo:
        return redirect(
            url_for(
                "auth.login", error=_("OIDC sign-in failed: no identity returned")
            )
        )

    success, message = handle_oidc_login(config, userinfo)
    if success:
        return redirect("/")

    return redirect(url_for("auth.login", error=message))


# ── Logout ────────────────────────────────────────────────────────────


@auth_bp.route("/logout", methods=["GET"])
@login_required
def logout():
    """Terminate session and redirect to login page."""
    logout_user()
    return redirect(url_for("auth.login"))
