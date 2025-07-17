import os
import urllib.parse

import requests
from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from app.extensions import db
from app.models import Invitation, MediaServer, Settings, User
from app.services.invites import is_invite_valid
from app.services.media.plex import handle_oauth_token

public_bp = Blueprint("public", __name__)


# ─── Landing “/” ──────────────────────────────────────────────────────────────
@public_bp.route("/")
def root():
    # check if admin_username exists
    admin_setting = Settings.query.filter_by(key="admin_username").first()
    if not admin_setting:
        return redirect("/setup/")  # installation wizard
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
    from app.services.invitation_flow import InvitationFlowManager

    manager = InvitationFlowManager()
    result = manager.process_invitation_display(code)
    return result.to_flask_response()


# ─── Unified invitation processing ─────────────────────────────────────────
@public_bp.route("/invitation/process", methods=["POST"])
def process_invitation():
    """Unified route for processing all invitation types"""
    from app.services.invitation_flow import InvitationFlowManager

    manager = InvitationFlowManager()
    form_data = request.form.to_dict()
    result = manager.process_invitation_submission(form_data)
    return result.to_flask_response()


# ─── POST /join  (Legacy Plex OAuth route - kept for compatibility) ────────
@public_bp.route("/join", methods=["POST"])
def join():
    code = request.form.get("code")
    token = request.form.get("token")

    print("Got Token: ", token)

    invitation = None
    if code:
        invitation = Invitation.query.filter(
            db.func.lower(Invitation.code) == code.lower()
        ).first()
    valid, msg = (
        is_invite_valid(code) if code else (False, "No invitation code provided")
    )
    if not valid:
        # server_name for rendering error
        name_setting = Settings.query.filter_by(key="server_name").first()
        server_name = name_setting.value if name_setting else None

        return render_template(
            "user-plex-login.html", name=server_name, code=code, code_error=msg
        )

    server = (invitation.server if invitation else None) or MediaServer.query.first()
    server_type = server.server_type if server else None

    from flask import current_app

    if server_type == "plex":
        # run Plex OAuth invite immediately (blocking – we need the DB row afterwards)
        if token and code:
            handle_oauth_token(current_app, token, code)

        # Determine if there are additional servers attached to the invite
        extra = [
            s
            for s in (invitation.servers if invitation else [])
            if s.server_type != "plex"
        ]

        if extra:
            # Stash the token & email lookup hint in session so we can provision others later
            session["invite_code"] = code
            session["invite_token"] = token
            return redirect(url_for("public.password_prompt", code=code))

        # No other servers → continue to wizard as before
        session["wizard_access"] = code
        return redirect(url_for("wizard.start"))
    if server_type in (
        "jellyfin",
        "emby",
        "audiobookshelf",
        "romm",
        "kavita",
        "komga",
    ):
        return render_template(
            "welcome-jellyfin.html", code=code, server_type=server_type
        )

    # fallback if server_type missing/unsupported
    return render_template("invalid-invite.html", error="Configuration error.")


@public_bp.route("/health", methods=["GET"])
def health():
    # If you need to check DB connectivity, do it here.
    return jsonify(status="ok"), 200


@public_bp.route("/static/manifest.json")
def manifest():
    """Serve the PWA manifest file with correct content type"""
    return send_from_directory(
        os.path.join(current_app.root_path, "static"),
        "manifest.json",
        mimetype="application/manifest+json",
    )


# ─── Password prompt for multi-server invites ───────────────────────────────


@public_bp.route("/j/<code>/password", methods=["GET", "POST"])
def password_prompt(code):
    invitation = Invitation.query.filter(
        db.func.lower(Invitation.code) == code.lower()
    ).first()

    if not invitation:
        return render_template("invalid-invite.html", error="Invalid invite")

    # ensure Plex has been processed
    # (a user row with this code and plex server_id should exist)
    plex_server = next((s for s in invitation.servers if s.server_type == "plex"), None)

    plex_user = None
    if plex_server:
        plex_user = User.query.filter_by(code=code, server_id=plex_server.id).first()

    if request.method == "POST":
        pw = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        if pw != confirm or len(pw) < 8:
            return render_template(
                "choose-password.html",
                code=code,
                error="Passwords do not match or too short (8 chars).",
            )

        # Fallback: generate strong password if checkbox ticked or blank
        if request.form.get("generate") or pw.strip() == "":
            import secrets
            import string

            pw = "".join(
                secrets.choice(string.ascii_letters + string.digits) for _ in range(16)
            )

        # Provision accounts on remaining servers
        from app.services.invites import mark_server_used
        from app.services.media.service import get_client_for_media_server

        for srv in invitation.servers:
            if srv.server_type == "plex":
                continue  # already done

            client = get_client_for_media_server(srv)

            username = (
                plex_user.username
                if plex_user
                else (plex_user.email.split("@")[0] if plex_user else "wizarr")
            )
            email = plex_user.email if plex_user else "user@example.com"

            try:
                if srv.server_type in ("jellyfin", "emby"):
                    uid = client.create_user(username, pw)
                elif srv.server_type == "audiobookshelf" or srv.server_type == "romm":
                    uid = client.create_user(username, pw, email=email)
                else:
                    continue  # unknown server type

                # set library permissions (simplified: full access)

                # store local DB row
                new_user = User()
                new_user.username = username
                new_user.email = email
                new_user.token = uid
                new_user.code = code
                new_user.server_id = srv.id
                db.session.add(new_user)
                db.session.commit()

                invitation.used_by = invitation.used_by or new_user
                mark_server_used(invitation, srv.id)
            except Exception as exc:
                db.session.rollback()
                import logging

                logging.error("Failed to provision user on %s: %s", srv.name, exc)

        session["wizard_access"] = code
        return redirect(url_for("wizard.start"))

    # GET request – show form
    return render_template("choose-password.html", code=code)


# ─── Image proxy to allow internal artwork URLs ─────────────────────────────
@public_bp.route("/image-proxy")
def image_proxy():
    raw = request.args.get("url")
    if not raw:
        return Response(status=400)
    url = urllib.parse.unquote_plus(raw)
    # rudimentary security – allow only http/https
    if not url.startswith(("http://", "https://")):
        return Response(status=400)
    try:
        r = requests.get(url, timeout=10, stream=True)
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "image/jpeg")
        resp = Response(r.content, content_type=content_type)
        # cache 1h
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp
    except Exception:
        return Response(status=502)
