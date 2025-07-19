import logging
import os

from flask import Blueprint, redirect, render_template, request, url_for
from flask_babel import _
from flask_login import login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from app.extensions import db, limiter
from app.models import AdminAccount, AdminUser, Settings

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if os.getenv("DISABLE_BUILTIN_AUTH", "").lower() == "true":
        login_user(AdminUser(), remember=bool(request.form.get("remember")))
        return redirect("/")

    if request.method == "GET":
        # Check if there are any passkeys registered in the system
        from app.models import WebAuthnCredential

        has_passkeys = WebAuthnCredential.query.first() is not None
        return render_template("login.html", has_passkeys=has_passkeys)

    username = request.form.get("username")
    password = request.form.get("password")

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

    # Check if there are any passkeys registered for error page
    from app.models import WebAuthnCredential

    has_passkeys = WebAuthnCredential.query.first() is not None
    return render_template(
        "login.html", error=_("Invalid username or password"), has_passkeys=has_passkeys
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
    account = AdminAccount.query.get(user_id)
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


# ── Logout ────────────────────────────────────────────────────────────


@auth_bp.route("/logout", methods=["GET"])
@login_required
def logout():
    """Terminate session and redirect to login page."""
    logout_user()
    return redirect(url_for("auth.login"))
