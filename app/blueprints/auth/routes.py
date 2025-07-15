import logging
import os

from flask import Blueprint, redirect, render_template, request, url_for
from flask_babel import _
from flask_login import login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import AdminAccount, AdminUser, Settings

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if os.getenv("DISABLE_BUILTIN_AUTH", "").lower() == "true":
        login_user(AdminUser(), remember=bool(request.form.get("remember")))
        return redirect("/")

    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    # ── 1) Multi-admin accounts (preferred) ────────────────────────────
    if (
        account := AdminAccount.query.filter_by(username=username).first()
    ) and account.check_password(password):
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

    return render_template("login.html", error=_("Invalid username or password"))


# ── Logout ────────────────────────────────────────────────────────────


@auth_bp.route("/logout", methods=["GET"])
@login_required
def logout():
    """Terminate session and redirect to login page."""
    logout_user()
    return redirect(url_for("auth.login"))
