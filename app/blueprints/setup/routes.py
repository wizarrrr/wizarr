# app/blueprints/setup/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from flask_login import login_user

from ...extensions import db
from ...models import Settings, AdminUser
from ...forms.setup import AdminAccountForm
from ...forms.settings import SettingsForm
from ...services.servers import check_plex, check_jellyfin
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

    # ───── Step 1: create admin account ───────────────────────────
    if not s["admin_username"].value or not s["admin_password"].value:
        form = AdminAccountForm()
        if form.validate_on_submit():
            s["admin_username"].value = form.username.data
            s["admin_password"].value = generate_password_hash(form.password.data, "scrypt")
            db.session.commit()
            login_user(AdminUser())
            flash("Admin account created – let’s hook up your media server.", "success")
            # → Redirect into server‐settings in setup mode
            # remember we’re still in setup
            session["in_setup"] = True
            
            return redirect(url_for("settings.server_settings"))

        return render_template("setup/admin_account.html", form=form)

    # If admin already exists, just forward you into server settings
    return redirect(url_for("settings.server_settings", setup=1))

def _probe_server(form):
    if form.server_type.data == "plex":
        ok = check_plex(form.server_url.data, form.api_key.data)
    else:
        ok = check_jellyfin(form.server_url.data, form.api_key.data)

    if not ok:
        flash("Couldn’t reach your server – double-check the URL/token.", "danger")
    return ok
