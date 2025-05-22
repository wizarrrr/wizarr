# app/blueprints/settings/routes.py
import logging

from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session, make_response

from flask_login import login_required
from flask_babel import _

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

@settings_bp.get("/")
@login_required
def page():
    return render_template("settings/page.html")


@settings_bp.route("/server", methods=["GET", "POST"])
@login_required
def server_settings():
    setup_mode = bool(session.get("in_setup"))

    current = _load_settings()
    form = SettingsForm(
        formdata=request.form if request.method == "POST" else None,
        data=current,
    )

    if form.validate_on_submit():
        data = form.data.copy()
        data.pop("csrf_token", None)
        # handle multi-select libraries
        selected = request.form.getlist("libraries")
        data["libraries"] = ", ".join(selected) if selected else current.get("libraries", "")

        if not _check_server_connection(data):
            # re-render in either setup or normal mode
            return render_template("partials/server_form.html", form=form, setup_mode=setup_mode)


        # save settings to DB
        data['server_verified'] = True
        _save_settings(data)
        flash("Settings saved successfully!", "success")

        # if we were in setup, jump to admin dashboard
        if setup_mode:
            session.pop("in_setup", None)
            resp = make_response("", 204)
            resp.headers["HX-Redirect"] = url_for("admin.dashboard")
            return resp

        # otherwise stay on settings page
        current.update(data)

    # If HTMX partial, or POST with errors, just re-render the form
    if request.headers.get("HX-Request") or (request.method == "POST" and form.errors):
        return render_template("partials/server_form.html", form=form, setup_mode=setup_mode)

    # Normal GET (non-HTMX) and not in setup: show settings index
    return redirect(url_for("settings.page"))

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