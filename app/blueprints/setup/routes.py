# app/blueprints/setup/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_user

from ...extensions import db
from ...models import Settings, AdminUser, AdminAccount, MediaServer
from ...forms.setup import AdminAccountForm
from ...forms.settings import SettingsForm
from ...services.servers import check_plex, check_jellyfin, check_emby, check_audiobookshelf
from sqlalchemy.exc import IntegrityError

setup_bp = Blueprint("setup", __name__, url_prefix="/setup")


def _settings_as_dict():
    """All settings as {key: Settings instance}."""
    return {s.key: s for s in Settings.query.all()}


def _ensure_keys_exist():
    """Insert missing rows so later code can rely on them."""
    default_keys = [
        "server_type", "admin_username", "admin_password", "server_verified",
        "server_url", "api_key", "server_name", "libraries",
        "overseerr_url", "ombi_api_key", "discord_id", "custom_html"
    ]
    for key in default_keys:
        if not Settings.query.filter_by(key=key).first():
            db.session.add(Settings(key=key, value=None))
    db.session.commit()


@setup_bp.route("/", methods=["GET", "POST"])
def onboarding():
    _ensure_keys_exist()
    s = _settings_as_dict()

    # ── Step 1: create admin account ───────────────────────────
    if not AdminAccount.query.first():
        form = AdminAccountForm()
        if form.validate_on_submit():
            # Store credentials in new AdminAccount model
            account = AdminAccount(username=form.username.data)
            account.set_password(form.password.data)
            db.session.add(account)

            # Also persist username/password to Settings for backward
            # compatibility – this will be removed in a future release once
            # the entire codebase migrates.
            s["admin_username"].value = form.username.data
            s["admin_password"].value = account.password_hash

            db.session.commit()

            login_user(account)
            flash("Admin account created – welcome!", "success")
            # → Redirect straight to admin dashboard instead of the onboarding wizard
            session["in_setup"] = True
            return redirect(url_for("admin.dashboard"))
        return render_template("setup/admin_account.html", form=form)

    # If admin already exists, check if a MediaServer exists
    if not MediaServer.query.first():
        session["in_setup"] = True
        return redirect(url_for("settings.page"))
    # Setup complete, go to admin
    return redirect(url_for("admin.dashboard"))

def _probe_server(form):
    if form.server_type.data == "plex":
        ok = check_plex(form.server_url.data, form.api_key.data)
    elif form.server_type.data == "emby":
        ok = check_emby(form.server_url.data, form.api_key.data)
    elif form.server_type.data == "audiobookshelf":
        ok = check_audiobookshelf(form.server_url.data, form.api_key.data)
    else:
        ok = check_jellyfin(form.server_url.data, form.api_key.data)

    if not ok:
        flash("Couldn't reach your server – double-check the URL/token.", "danger")
    return ok
