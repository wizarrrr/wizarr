from flask import Blueprint, redirect, render_template, send_from_directory, request, jsonify, url_for
import os, threading
from app.extensions import db
from app.models import Settings
from app.services.invites import is_invite_valid
from app.services.media.plex import handle_oauth_token
from app.services.ombi_client import run_all_importers
from app.forms.join import JoinForm

public_bp = Blueprint("public", __name__)

# ─── Landing “/” ──────────────────────────────────────────────────────────────
@public_bp.route("/")
def root():
    # check if admin_username exists
    admin_setting = Settings.query.filter_by(key="admin_username").first()
    if not admin_setting:
        return redirect("/setup/")              # installation wizard
    return redirect("/admin")

# ─── Favicon ─────────────────────────────────────────────────────────────────
@public_bp.route("/favicon.ico")
def favicon():
    return send_from_directory(
        public_bp.root_path.replace("blueprints/public", "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )

# ─── Invite link  /j/<code> ─────────────────────────────────────────────────
@public_bp.route("/j/<code>")
def invite(code):
    valid, msg = is_invite_valid(code)
    if not valid:
        return render_template("invalid-invite.html", error=msg)

    # fetch server_type setting
    server_type_setting = Settings.query.filter_by(key="server_type").first()
    server_type = server_type_setting.value if server_type_setting else None

    if server_type == "jellyfin" or server_type == "emby":
        form = JoinForm()
        form.code.data = code
        return render_template(
            "welcome-jellyfin.html",
            form=form,
            server_type=server_type,
        )
    return render_template("user-plex-login.html", code=code)

# ─── POST /join  (Plex OAuth or Jellyfin signup) ────────────────────────────
@public_bp.route("/join", methods=["POST"])
def join():
    code  = request.form.get("code")
    token = request.form.get("token")

    valid, msg = is_invite_valid(code)
    if not valid:
        # server_name for rendering error
        name_setting = Settings.query.filter_by(key="server_name").first()
        server_name = name_setting.value if name_setting else None

        return render_template(
            "user-plex-login.html",
            name=server_name,
            code=code,
            code_error=msg
        )

    # fetch server_type one more time
    server_type_setting = Settings.query.filter_by(key="server_type").first()
    server_type = server_type_setting.value if server_type_setting else None

    
    
    from flask import current_app
    app = current_app._get_current_object()
    
    if server_type == "plex":
        # run Plex OAuth in background
        threading.Thread(
            target=handle_oauth_token,
            args=(app, token, code),
            daemon=True
        ).start()
        return redirect(url_for("wizard.start"))
    elif server_type == "jellyfin" or server_type == "emby":
        return render_template("welcome-jellyfin.html", code=code, server_type=server_type)

    # fallback if server_type missing/unsupported
    return render_template("invalid-invite.html", error="Configuration error.")

@public_bp.route("/health", methods=["GET"])
def health():
    # If you need to check DB connectivity, do it here.
    return jsonify(status="ok"), 200