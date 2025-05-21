# app/blueprints/setup/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
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
            return redirect(url_for(".onboarding"))

        return render_template("setup/admin_account.html", form=form)

    # ───── Step 2: verify server connection ───────────────────────
    if not (s["server_verified"].value and s["server_verified"].value.lower() == "true"):
        form = SettingsForm(install_mode=True)

        if form.validate_on_submit():
            if not _probe_server(form):
                return render_template("setup/server_details.html", form=form)

            # write everything in one transaction
            try:
                for field, row in s.items():
                    if field in form.data:
                        row.value = (form.data[field] or "").strip()
                # mark as verified
                s["server_verified"].value = "true"
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Database error saving settings.", "danger")
                return render_template("setup/server_details.html", form=form,
    setup_mode=True)

            flash("Server verified – setup finished!", "success")
              # ← you’re now authenticated
            return redirect(url_for("admin.dashboard"))

        return render_template("setup/server_details.html", form=form,
    setup_mode=True)

    # Already configured – bounce to admin
    return redirect(url_for("admin.dashboard"))

def _probe_server(form):
    if form.server_type.data == "plex":
        ok = check_plex(form.server_url.data, form.api_key.data)
    else:
        ok = check_jellyfin(form.server_url.data, form.api_key.data)

    if not ok:
        flash("Couldn’t reach your server – double-check the URL/token.", "danger")
    return ok
