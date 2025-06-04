# app/blueprints/settings/routes.py
import logging

from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session, make_response

from flask_login import login_required
from flask_babel import _

from app.services.media.service import scan_libraries as scan_media
from ...models import Settings, Library
from ...forms.settings import SettingsForm
from ...services.servers  import check_plex, check_jellyfin
from ...extensions import db

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

def _load_settings() -> dict:
    # Load all rows and build a dict
    settings = {s.key: s.value for s in Settings.query.all()}
    
    # Convert specific boolean fields from strings to booleans
    boolean_fields = ["allow_downloads_plex", "allow_tv_plex"]
    for field in boolean_fields:
        if field in settings:
            settings[field] = settings[field].lower() == "true"
    
    return settings

def _save_settings(data: dict) -> None:
    """Upsert each key/value in one go."""
    try:
        for key, value in data.items():
            # Convert boolean values to "true"/"false" strings
            if isinstance(value, bool):
                value = "true" if value else "false"
            
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
    return render_template("settings/index.html")


@settings_bp.route("/server", methods=["GET", "POST"])
@login_required
def server_settings():
    setup_mode = bool(session.get("in_setup"))
    current = _load_settings()  # { key: value }
    
    # load all known libraries to build checkboxes
    all_libs = Library.query.order_by(Library.name).all()
    # turn comma-list into list of external_ids
    prechecked = set((current.get("libraries") or "").split(", "))

    form = SettingsForm(
        formdata=request.form if request.method=="POST" else None,
        data=current
    )

    if form.validate_on_submit():
        data = form.data.copy()
        data.pop("csrf_token", None)

        chosen = set(request.form.getlist("libraries"))
        # Only update enabled state if at least one library is selected
        if chosen:
            for lib in Library.query:
                lib.enabled = (lib.external_id in chosen)
            db.session.commit()

        if not _check_server_connection(data):
            # HTMX‐render of the same form with errors
            return render_template(
                "settings/partials/server_form.html",
                form=form,
                all_libs=all_libs,
                prechecked=set(chosen),
                setup_mode=setup_mode
            )

        # persist into Settings
        data["server_verified"] = "true"
        _save_settings(data)
        flash("Settings saved successfully!", "success")

        if setup_mode:
            print("Setup mode: redirecting to dashboard")
            # consume the "in_setup" flag and tell HTMX to redirect
            session.pop("in_setup")
            resp = make_response("", 204)
            resp.headers["HX-Redirect"] = url_for("admin.dashboard")
            return resp

        # re-render form in normal mode
        prechecked = set(chosen)

    # GET or POST-with-errors: just re-render the partial
    if request.headers.get("HX-Request"):
        return render_template(
            "settings/partials/server_form.html",
            form=form,
            all_libs=all_libs,
            prechecked=prechecked,
            setup_mode=setup_mode
        )

    # fallback: non‐HTMX GET → back to index
    return redirect(url_for("settings.page"))

@settings_bp.route("/scan-libraries", methods=["POST"])
@login_required
def scan_libraries():
    # 1) credentials: prefer form → fallback to DB
    s = {r.key: r.value for r in Settings.query.all()}
    stype = request.form.get("server_type") or s["server_type"]
    url   = request.form.get("server_url")    or s["server_url"]
    key   = request.form.get("api_key")       or s["api_key"]

    if not url or not key:
        return jsonify({"error":"missing"}), 400

    # 2) fetch upstream libraries
    try:
        raw = scan_media(url=url, token=key, server_type=stype)
        # unify into list of (external_id, display_name)
        items = raw.items() if isinstance(raw, dict) else [(name, name) for name in raw]
    except Exception as exc:
        logging.warning("Library scan failed: %s", exc)
        return "<div class='text-red-500'>%s</div>" % _("Library scan failed")

    # 3) upsert into our Library table
    seen_ids = set()
    for fid, name in items:
        seen_ids.add(fid)
        lib = Library.query.filter_by(external_id=fid).first()
        if lib:
            lib.name = name   # keep names fresh
        else:
            db.session.add(Library(external_id=fid, name=name))
    # delete any that upstream no longer offers
    Library.query.filter(~Library.external_id.in_(seen_ids)).delete(synchronize_session=False)
    db.session.commit()

    # 4) render checkboxes off our Library.enabled
    all_libs = Library.query.order_by(Library.name).all()
    return render_template(
      "partials/library_checkboxes.html",
      libs=all_libs
    )

