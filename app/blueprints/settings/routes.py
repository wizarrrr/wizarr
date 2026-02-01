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

from app.forms.ldap import LDAPSettingsForm
from app.services.expiry import disable_or_delete_user_if_expired
from app.services.ldap.encryption import encrypt_credential
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

    # 3) Delete all old libraries and insert fresh ones
    # Note: This assumes single-server legacy setup (settings route)
    Library.query.delete()
    db.session.flush()

    # Insert fresh libraries with correct external IDs
    for fid, name in items:
        lib = Library()
        lib.external_id = fid
        lib.name = name
        lib.enabled = True
        db.session.add(lib)
    db.session.commit()

    # 4) render checkboxes off our Library.enabled
    all_libs = Library.query.order_by(Library.name).all()
    return render_template("partials/library_checkboxes.html", libs=all_libs)


@settings_bp.route("/general", methods=["GET", "POST"])
@login_required
def general_settings():
    import os

    current = _load_settings()
    form = GeneralSettingsForm(
        formdata=request.form if request.method == "POST" else None, data=current
    )
    if form.validate_on_submit():
        data = form.data.copy()
        _save_settings(data)
        flash(_("Settings saved successfully!"), "success")
        # Reload settings from database and create a fresh form to display updated values
        current = _load_settings()
        form = GeneralSettingsForm(data=current)

    app_version = os.getenv("APP_VERSION", "dev")

    if request.headers.get("HX-Request"):
        return render_template(
            "settings/general.html", form=form, app_version=app_version
        )
    return redirect(url_for("settings.page"))


@settings_bp.route("/clean-expired-users", methods=["POST"])
@login_required
def clean_expired_users():
    """Manually trigger cleanup of all expired users."""
    try:
        processed_ids = disable_or_delete_user_if_expired()
        count = len(processed_ids)

        if count > 0:
            flash(
                _("Successfully cleaned {count} expired user(s).").format(count=count),
                "success",
            )
            logging.info("🧹 Manual cleanup: Processed %s expired users.", count)
        else:
            flash(_("No expired users found to clean."), "info")

        # Return the button HTML for HTMX swap
        return """
        <button type="button"
                hx-post="{url}"
                hx-target="#clean-expired-users-container"
                hx-swap="innerHTML"
                hx-indicator="#clean-expired-indicator"
                hx-confirm="{confirm}"
                class="inline-flex items-center px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 focus:outline-none focus:ring-4 focus:ring-red-300 dark:focus:ring-red-800 text-sm font-medium shadow-xs transition-colors">
          <svg id="clean-expired-indicator" class="htmx-indicator w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <svg class="w-4 h-4 mr-2 [.htmx-request_&]:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
          </svg>
          {label}
        </button>
        """.format(
            url=url_for("settings.clean_expired_users"),
            confirm=_(
                "Are you sure you want to clean all expired users? This action cannot be undone."
            ),
            label=_("Clean Expired Users"),
        )
    except Exception as exc:
        logging.exception("Failed to clean expired users: %s", exc)
        flash(
            _("Failed to clean expired users: {error}").format(error=str(exc)), "error"
        )
        return """
        <button type="button"
                hx-post="{url}"
                hx-target="#clean-expired-users-container"
                hx-swap="innerHTML"
                hx-indicator="#clean-expired-indicator"
                hx-confirm="{confirm}"
                class="inline-flex items-center px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 focus:outline-none focus:ring-4 focus:ring-red-300 dark:focus:ring-red-800 text-sm font-medium shadow-xs transition-colors">
          <svg id="clean-expired-indicator" class="htmx-indicator w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <svg class="w-4 h-4 mr-2 [.htmx-request_&]:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
          </svg>
          {label}
        </button>
        """.format(
            url=url_for("settings.clean_expired_users"),
            confirm=_(
                "Are you sure you want to clean all expired users? This action cannot be undone."
            ),
            label=_("Clean Expired Users"),
        )


# ────────────────────────────────────────────────────────────────────────────
# LDAP Settings Routes (2025-12)
# ────────────────────────────────────────────────────────────────────────────


@settings_bp.route("/ldap", methods=["GET", "POST"])
@login_required
def ldap_settings():
    """LDAP configuration page."""
    from app.forms.ldap import LDAPSettingsForm
    from app.models import LDAPConfiguration, LDAPGroup
    from app.services.ldap.encryption import encrypt_credential

    config = LDAPConfiguration.query.first()
    form = LDAPSettingsForm()

    # Populate admin group choices from synced LDAP groups
    groups = LDAPGroup.query.order_by(LDAPGroup.cn).all()
    group_choices = [("", "-- None --")] + [(g.dn, g.cn) for g in groups]
    form.admin_group_dn.choices = group_choices

    if form.validate_on_submit():
        if not config:
            config = LDAPConfiguration()
            db.session.add(config)

        # Update configuration from form
        config.enabled = form.enabled.data
        config.server_url = form.server_url.data
        config.use_tls = form.use_tls.data
        config.verify_cert = form.verify_cert.data
        config.service_account_dn = form.service_account_dn.data

        # Only update password if provided
        if form.service_account_password.data:
            config.service_account_password_encrypted = encrypt_credential(
                form.service_account_password.data
            )

        config.user_base_dn = form.user_base_dn.data
        config.user_search_filter = form.user_search_filter.data
        config.user_object_class = form.user_object_class.data
        config.username_attribute = form.username_attribute.data
        config.email_attribute = form.email_attribute.data
        config.group_base_dn = form.group_base_dn.data
        config.group_object_class = form.group_object_class.data
        config.group_member_attribute = form.group_member_attribute.data
        config.allow_admin_bind = form.allow_admin_bind.data
        config.admin_group_dn = form.admin_group_dn.data

        db.session.commit()
        flash(_("LDAP configuration saved successfully"), "success")
        return render_template("settings/ldap.html", form=form, config=config)

    # Populate form with existing config
    if config and request.method == "GET":
        form.enabled.data = config.enabled
        form.server_url.data = config.server_url
        form.use_tls.data = config.use_tls
        form.verify_cert.data = config.verify_cert
        form.service_account_dn.data = config.service_account_dn
        form.user_base_dn.data = config.user_base_dn
        form.user_search_filter.data = config.user_search_filter
        form.user_object_class.data = config.user_object_class
        form.username_attribute.data = config.username_attribute
        form.email_attribute.data = config.email_attribute
        form.group_base_dn.data = config.group_base_dn
        form.group_object_class.data = config.group_object_class
        form.group_member_attribute.data = config.group_member_attribute
        form.allow_admin_bind.data = config.allow_admin_bind
        form.admin_group_dn.data = config.admin_group_dn

    return render_template("settings/ldap.html", form=form, config=config)


@settings_bp.route("/ldap/test", methods=["POST"])
@login_required
def test_ldap_connection():
    """Test LDAP connection (HTMX endpoint)."""
    from app.models import LDAPConfiguration
    from app.services.ldap.client import LDAPClient

    # Try to get existing config for password fallback
    existing_config = LDAPConfiguration.query.first()

    config = LDAPConfiguration()
    form = LDAPSettingsForm()

    config.enabled = form.enabled.data
    config.server_url = form.server_url.data
    config.use_tls = form.use_tls.data
    config.verify_cert = form.verify_cert.data
    config.service_account_dn = form.service_account_dn.data

    # Use new password if provided, otherwise fall back to existing encrypted password
    if form.service_account_password.data:
        config.service_account_password_encrypted = encrypt_credential(
            form.service_account_password.data
        )
    elif existing_config:
        config.service_account_password_encrypted = (
            existing_config.service_account_password_encrypted
        )

    client = LDAPClient(config)
    success, message = client.test_connection()

    if success:
        return f"""
        <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
            <p class="text-sm text-green-800 dark:text-green-200">✓ {message}</p>
        </div>
        """
    return f"""
    <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p class="text-sm text-red-800 dark:text-red-200">✗ {message}</p>
    </div>
    """


@settings_bp.route("/ldap/groups/sync", methods=["POST"])
@login_required
def sync_ldap_groups():
    """Synchronize LDAP groups into database (HTMX endpoint)."""
    from app.models import LDAPConfiguration, LDAPGroup
    from app.services.ldap.client import LDAPClient

    config = LDAPConfiguration.query.first()
    if not config or not config.enabled:
        return """
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p class="text-sm text-red-800 dark:text-red-200">LDAP not configured or disabled</p>
        </div>
        """

    client = LDAPClient(config)
    groups = client.search_groups()

    if not groups:
        return """
        <div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
            <p class="text-sm text-yellow-800 dark:text-yellow-200">No groups found in LDAP</p>
        </div>
        """

    synced_count = 0
    for group_data in groups:
        existing = LDAPGroup.query.filter_by(dn=group_data["dn"]).first()
        if not existing:
            group = LDAPGroup(
                dn=group_data["dn"],
                cn=group_data["cn"],
                description=group_data.get("description"),
            )
            db.session.add(group)
            synced_count += 1

    db.session.commit()

    # Get updated groups for admin dropdown
    all_groups = LDAPGroup.query.order_by(LDAPGroup.cn).all()
    group_options = '<option value="">-- None --</option>'
    for g in all_groups:
        group_options += f'<option value="{g.dn}">{g.cn}</option>'

    # Return status message + OOB update for admin group dropdown
    return f"""
    <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
        <p class="text-sm text-green-800 dark:text-green-200">
            ✓ Synchronized {synced_count} new group{"s" if synced_count != 1 else ""}
            (Total: {len(groups)} group{"s" if len(groups) != 1 else ""} in LDAP)
        </p>
    </div>
    <select id="admin_group_dn_select"
            name="admin_group_dn"
            hx-swap-oob="true"
            class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary focus:border-primary block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white">
        {group_options}
    </select>
    """


@settings_bp.route("/ldap/users/sync-all", methods=["POST"])
@login_required
def sync_all_ldap_users():
    """Automatically sync all users from LDAP and show unified user list.

    This imports all new LDAP users that don't exist in Wizarr yet,
    then returns the updated unified user list.
    """
    from app.models import LDAPConfiguration, User
    from app.services.ldap.user_sync import import_ldap_user, list_ldap_users

    ldap_config = LDAPConfiguration.query.filter_by(enabled=True).first()
    if not ldap_config:
        return """
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p class="text-sm text-red-800 dark:text-red-200">✗ LDAP is not configured</p>
        </div>
        """

    # Get all LDAP users
    success, result = list_ldap_users()
    if not success:
        return f"""
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p class="text-sm text-red-800 dark:text-red-200">✗ Failed to list LDAP users: {result}</p>
        </div>
        """

    ldap_users = result

    # Import each user that doesn't exist yet
    imported_count = 0
    skipped_count = 0
    errors = []

    for ldap_user in ldap_users:
        username = ldap_user["username"]

        # Check if user already exists
        existing = User.query.filter_by(username=username).first()
        if existing:
            skipped_count += 1
            continue

        # Import the user
        import_success, import_msg = import_ldap_user(username)
        if import_success:
            imported_count += 1
        else:
            errors.append(f"{username}: {import_msg}")

    # Build success/error message
    msg_html = '<div class="space-y-2 mb-4">'

    if imported_count > 0:
        msg_html += f"""
        <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
            <p class="text-sm text-green-800 dark:text-green-200">
                ✓ Imported {imported_count} new user{"s" if imported_count != 1 else ""} from LDAP
            </p>
        </div>
        """

    if skipped_count > 0:
        msg_html += f"""
        <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <p class="text-sm text-blue-800 dark:text-blue-200">
                ℹ Skipped {skipped_count} user{"s" if skipped_count != 1 else ""} (already in Wizarr)
            </p>
        </div>
        """

    if errors:
        msg_html += f"""
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p class="text-sm text-red-800 dark:text-red-200">✗ Errors during import:</p>
            <ul class="mt-2 text-xs text-red-700 dark:text-red-300 list-disc list-inside">
                {"".join(f"<li>{err}</li>" for err in errors)}
            </ul>
        </div>
        """

    if imported_count == 0 and skipped_count == 0 and not errors:
        msg_html += """
        <div class="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <p class="text-sm text-gray-600 dark:text-gray-400">No users to import</p>
        </div>
        """

    msg_html += "</div>"

    return msg_html
