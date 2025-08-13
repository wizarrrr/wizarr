# app/blueprints/settings/routes.py
import base64
import logging

from flask import (
    Blueprint,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_babel import _
from flask_login import login_required

from app.services.media.service import scan_libraries as scan_media

from ...extensions import db
from ...forms.general import GeneralSettingsForm
from ...forms.settings import SettingsForm
from ...models import Library, MediaServer, Settings
from ...services.servers import (
    check_audiobookshelf,
    check_emby,
    check_jellyfin,
    check_plex,
    check_romm,
)

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


def _load_settings() -> dict:
    # Load all rows and build a dict
    settings = {s.key: s.value for s in Settings.query.all()}

    # Convert specific boolean fields from strings to booleans
    boolean_fields = ["allow_downloads", "allow_live_tv", "wizard_acl_enabled"]
    for field in boolean_fields:
        if field in settings and settings[field] is not None:
            settings[field] = str(settings[field]).lower() == "true"

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
                setting = Settings()
                setting.key = key
                setting.value = value
                db.session.add(setting)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def _check_server_connection(data: dict) -> tuple[bool, str]:
    stype = data["server_type"]
    if stype == "plex":
        return check_plex(data["server_url"], data["api_key"])
    if stype == "emby":
        return check_emby(data["server_url"], data["api_key"])
    if stype == "audiobookshelf":
        return check_audiobookshelf(data["server_url"], data["api_key"])
    if stype == "romm":
        # Derive token from supplied credentials if api_key missing
        token = data.get("api_key")
        if not token:
            username = data.get("server_username", "").strip()
            password = data.get("server_password", "").strip()
            if username and password:
                token = base64.b64encode(f"{username}:{password}".encode()).decode()
        return check_romm(data["server_url"], token or "")
    return check_jellyfin(data["server_url"], data["api_key"])


@settings_bp.get("")
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
        formdata=request.form if request.method == "POST" else None, data=current
    )

    if form.validate_on_submit():
        data = form.data.copy()

        chosen = set(request.form.getlist("libraries"))
        # Only update enabled state if at least one library is selected
        if chosen:
            for lib in Library.query:
                lib.enabled = lib.external_id in chosen
            db.session.commit()

        ok, error_msg = _check_server_connection(data)
        if not ok:
            # Add the error message to the form
            form.server_url.errors = [error_msg]
            # HTMX‐render of the same form with errors
            return render_template(
                "settings/partials/server_form.html",
                form=form,
                all_libs=all_libs,
                prechecked=set(chosen),
                setup_mode=setup_mode,
            )

        # Check if a MediaServer already exists
        existing_server = MediaServer.query.first()
        if existing_server:
            # Update existing server
            existing_server.name = data["server_name"]
            existing_server.server_type = data["server_type"]
            existing_server.url = data["server_url"]
            existing_server.api_key = data.get("api_key")
            existing_server.external_url = data.get("external_url")
            existing_server.allow_downloads = bool(data.get("allow_downloads"))
            existing_server.allow_live_tv = bool(data.get("allow_live_tv"))
            existing_server.verified = True
            db.session.commit()
        else:
            # Create new server
            server = MediaServer()
            server.name = data["server_name"]
            server.server_type = data["server_type"]
            server.url = data["server_url"]
            server.api_key = data.get("api_key")
            server.external_url = data.get("external_url")
            server.allow_downloads = bool(data.get("allow_downloads"))
            server.allow_live_tv = bool(data.get("allow_live_tv"))
            server.verified = True
            db.session.add(server)
            db.session.commit()

        # persist into Settings
        data["server_verified"] = "true"
        _save_settings(data)
        flash(_("Settings saved successfully!"), "success")

        if setup_mode:
            # Only mark setup complete and redirect if this is the first server
            if MediaServer.query.count() == 1:
                # Setup complete: first server added, redirect to dashboard
                session.pop("in_setup", None)

            # HTMX requests honour HX-Redirect header, regular form POSTs need a
            # classic HTTP redirect.  Support both so users are never stuck on
            # the settings page after first-time setup.
            if request.headers.get("HX-Request"):
                resp = make_response("", 204)
                resp.headers["HX-Redirect"] = url_for("admin.dashboard")
                return resp
            return redirect(url_for("admin.dashboard"))
        # re-render form in normal mode
        prechecked = set(chosen)

    # GET or POST-with-errors: just re-render the partial
    if request.headers.get("HX-Request"):
        return render_template(
            "settings/partials/server_form.html",
            form=form,
            all_libs=all_libs,
            prechecked=prechecked,
            setup_mode=setup_mode,
        )

    # fallback: non‐HTMX GET → back to index
    return redirect(url_for("settings.page"))


@settings_bp.route("/scan-libraries", methods=["POST"])
@login_required
def scan_libraries():
    # 1) credentials: prefer form → fallback to DB
    s = {r.key: r.value for r in Settings.query.all()}
    stype = request.form.get("server_type") or s.get("server_type")
    url = request.form.get("server_url") or s.get("server_url")
    key = request.form.get("api_key") or s.get("api_key")

    if stype == "romm" and (not key):
        username = request.form.get("server_username")
        password = request.form.get("server_password")
        if username and password:
            key = base64.b64encode(f"{username}:{password}".encode()).decode()

    if not url or not key:
        missing_fields = []
        if not url:
            missing_fields.append(_("Server URL"))
        if not key:
            missing_fields.append(
                _("API Key") if stype != "romm" else _("Username/Password")
            )

        error_message = _("Missing required fields: {fields}").format(
            fields=", ".join(missing_fields)
        )
        return f"<div class='text-red-500 p-3 border border-red-300 rounded-lg bg-red-50 dark:bg-red-900 dark:border-red-700'><strong>{_('Error')}:</strong> {error_message}</div>"

    # 2) fetch upstream libraries
    try:
        raw = scan_media(url=url, token=key, server_type=stype)
        # unify into list of (external_id, display_name)
        items = raw.items() if isinstance(raw, dict) else [(name, name) for name in raw]
    except Exception as exc:
        logging.warning("Library scan failed: %s", exc)
        error_message = str(exc) if str(exc) else _("Library scan failed")
        return f"<div class='text-red-500 p-3 border border-red-300 rounded-lg bg-red-50 dark:bg-red-900 dark:border-red-700'><strong>{_('Error')}:</strong> {error_message}</div>"

    # 3) upsert into our Library table
    seen_ids = set()
    for fid, name in items:
        seen_ids.add(fid)
        lib = Library.query.filter_by(external_id=fid).first()
        if lib:
            lib.name = name  # keep names fresh
        else:
            lib = Library()
            lib.external_id = fid
            lib.name = name
            db.session.add(lib)
    # delete any that upstream no longer offers
    Library.query.filter(~Library.external_id.in_(seen_ids)).delete(
        synchronize_session=False
    )
    db.session.commit()

    # 4) render checkboxes off our Library.enabled
    all_libs = Library.query.order_by(Library.name).all()
    return render_template("partials/library_checkboxes.html", libs=all_libs)


@settings_bp.route("/general", methods=["GET", "POST"])
@login_required
def general_settings():
    current = _load_settings()
    form = GeneralSettingsForm(
        formdata=request.form if request.method == "POST" else None, data=current
    )
    if form.validate_on_submit():
        data = form.data.copy()
        _save_settings(data)
        flash(_("Settings saved successfully!"), "success")
    if request.headers.get("HX-Request"):
        return render_template("settings/general.html", form=form)
    return redirect(url_for("settings.page"))
