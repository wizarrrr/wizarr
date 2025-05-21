# app/blueprints/settings/routes.py
import logging

from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required

from app.services.plex_client     import scan_libraries as scan_plex
from app.services.jellyfin_client import scan_libraries as scan_jf
from ...models     import Settings
from ...forms.settings import SettingsForm
from ...services.servers  import check_plex, check_jellyfin
from ...extensions import db

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

def _load_settings() -> dict:
    # Load all rows and build a dict
    return {s.key: s.value for s in Settings.query.all()}

def _save_settings(data: dict) -> None:
    """Upsert each key/value in one go."""
    try:
        for key, value in data.items():
            setting = Settings.query.filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                db.session.add(Settings(key=key, value=value))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

def _check_server_connection(data: dict) -> bool:
    stype = data["server_type"]
    if stype == "plex":
        return check_plex(data["server_url"], data["api_key"])
    return check_jellyfin(data["server_url"], data["api_key"])

@settings_bp.route("/", methods=["GET", "POST"])
@login_required
def secure_settings():
    current = _load_settings()

    form = SettingsForm(
        formdata=request.form if request.method == "POST" else None,
        data=current,
    )

    if form.validate_on_submit():
        data = form.data.copy()
        data.pop("csrf_token", None)

        # handle multi-select libraries field
        selected = request.form.getlist("libraries")
        data["libraries"] = ", ".join(selected) if selected else current.get("libraries", "")

        if not _check_server_connection(data):
            return render_template("settings.html", form=form)

        _save_settings(data)
        flash("Settings saved successfully!", "success")
        current.update(data)  # so form re-renders with fresh values

    # HTMX partial
    if request.headers.get("HX-Request"):
        return render_template("settings.html", form=form)

    # Show errors on failed POST
    if request.method == "POST" and form.errors:
        return render_template("settings.html", form=form)

    # Normal GET → back to dashboard
    return redirect(url_for("admin.dashboard"))

@settings_bp.route("/scan-libraries", methods=["POST"])
@login_required
def scan_libraries():
    # 1. credentials: prefer POSTed form data, fall back to DB
    s = _load_settings()                      # {'server_type': 'plex', …}

    stype = request.form.get("server_type") or s["server_type"]
    url   = request.form.get("server_url")    or s["server_url"]
    key   = request.form.get("api_key")       or s["api_key"]

    if not url or not key:
        return jsonify({"error": "missing"}), 400

    # 2. fetch list from Plex / Jellyfin
    try:
        names = scan_plex(url, key) if stype == "plex" else scan_jf(url, key)
        if not isinstance(names, list):                       # jellyfin dict→list
            names = list(names.keys())
    except Exception as exc:
        logging.warning("Library scan failed: %s", exc)
        return jsonify({"error": "connect"}), 400

    # 3. libraries already stored in Settings → pre-checked
    saved = s.get("libraries", "") 
    selected = [lib.strip() for lib in saved.split(",") if lib.strip()] if saved else []

    return render_template(
        "partials/library_checkboxes.html",
        libs=names,
        selected=selected,          # boxes ticked on *every* screen
    )