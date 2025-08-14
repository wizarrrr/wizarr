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

from app.extensions import db, limiter
from app.models import Invitation, MediaServer, Settings, User
from app.services.invites import is_invite_valid
from app.services.media.plex import PlexInvitationError, handle_oauth_token

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
@limiter.limit("50 per minute")
def invite(code):
    from app.services.invitation_flow import InvitationFlowManager

    manager = InvitationFlowManager()
    result = manager.process_invitation_display(code)
    return result.to_flask_response()


# ─── Unified invitation processing ─────────────────────────────────────────
@public_bp.route("/invitation/process", methods=["POST"])
@limiter.limit("20 per minute")
def process_invitation():
    """Unified route for processing all invitation types"""
    from app.services.invitation_flow import InvitationFlowManager

    manager = InvitationFlowManager()
    form_data = request.form.to_dict()
    result = manager.process_invitation_submission(form_data)
    return result.to_flask_response()


# ─── POST /join  (Legacy Plex OAuth route - kept for compatibility) ────────
@public_bp.route("/join", methods=["POST"])
@limiter.limit("20 per minute")
def join():
    code = request.form.get("code")
    token = request.form.get("token")

    invitation = None
    if code:
        invitation = Invitation.query.filter(
            db.func.lower(Invitation.code) == code.lower()
        ).first()
    valid, msg = (
        is_invite_valid(code) if code else (False, "No invitation code provided")
    )
    if not valid:
        # Resolve server name for rendering error
        from app.services.server_name_resolver import resolve_invitation_server_name

        # Try to get servers from invitation for error display
        servers = []
        if invitation and invitation.servers:
            servers = list(invitation.servers)
        elif invitation and invitation.server:
            servers = [invitation.server]

        server_name = resolve_invitation_server_name(servers)

        return render_template(
            "user-plex-login.html", server_name=server_name, code=code, code_error=msg
        )

    # Get the appropriate server for this invitation
    server = None
    if invitation:
        # Prioritize new many-to-many relationship
        if hasattr(invitation, "servers") and invitation.servers:
            # For legacy /join route, prioritize Plex servers first (backward compatibility)
            plex_servers = [s for s in invitation.servers if s.server_type == "plex"]
            server = plex_servers[0] if plex_servers else invitation.servers[0]
        # Fallback to legacy single server relationship
        elif invitation.server:
            server = invitation.server

    # Final fallback to any server (maintain existing behavior)
    if not server:
        server = MediaServer.query.first()
    server_type = server.server_type if server else None

    from flask import current_app

    if server_type == "plex":
        # run Plex OAuth invite immediately (blocking – we need the DB row afterwards)
        if token and code:
            try:
                handle_oauth_token(current_app, token, code)
            except PlexInvitationError as e:
                # Show user-friendly error message from Plex API
                name_setting = Settings.query.filter_by(key="server_name").first()
                server_name = name_setting.value if name_setting else None

                return render_template(
                    "user-plex-login.html",
                    server_name=server_name,
                    code=code,
                    code_error=f"Plex invitation failed: {e.message}",
                )
            except Exception as e:
                # Handle any other unexpected errors
                import logging

                logging.error(f"Unexpected error during Plex OAuth: {e}")

                name_setting = Settings.query.filter_by(key="server_name").first()
                server_name = name_setting.value if name_setting else None

                return render_template(
                    "user-plex-login.html",
                    server_name=server_name,
                    code=code,
                    code_error="An unexpected error occurred during invitation. Please try again or contact support.",
                )

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
        from app.forms.join import JoinForm

        # Get server name for the invitation using the new resolver if available
        try:
            from app.services.server_name_resolver import resolve_invitation_server_name

            servers = []
            if invitation and invitation.servers:
                servers = list(invitation.servers)
            elif invitation and invitation.server:
                servers = [invitation.server]
            elif server:
                servers = [server]

            server_name = resolve_invitation_server_name(servers)
        except ImportError:
            # Fallback to legacy approach if resolver not available
            name_setting = Settings.query.filter_by(key="server_name").first()
            server_name = name_setting.value if name_setting else "Media Server"

        form = JoinForm()
        form.code.data = code
        return render_template(
            "welcome-jellyfin.html",
            code=code,
            server_type=server_type,
            server_name=server_name,
            form=form,
        )

    # fallback if server_type missing/unsupported
    return render_template("invalid-invite.html", error="Configuration error.")


@public_bp.route("/health", methods=["GET"])
def health():
    # If you need to check DB connectivity, do it here.
    return jsonify(status="ok"), 200


@public_bp.route("/cinema-posters")
def cinema_posters():
    """Get movie poster URLs for cinema background display."""
    try:
        import time

        from flask import current_app

        from app.models import MediaServer
        from app.services.media.service import get_client_for_media_server

        # Cache key for poster URLs
        cache_key = "cinema_posters"
        cache_duration = 1800  # 30 minutes

        # Check cache first
        cached_data = current_app.config.get("POSTER_CACHE", {})
        cached_entry = cached_data.get(cache_key)

        if cached_entry and (time.time() - cached_entry["timestamp"]) < cache_duration:
            return jsonify(cached_entry["data"])

        # Get the primary media server (or first available)
        server = MediaServer.query.first()
        if not server:
            return jsonify([])

        # Get media client for the server
        client = get_client_for_media_server(server)

        # Check if client has get_movie_posters method
        poster_urls = []
        if hasattr(client, "get_movie_posters"):
            poster_urls = client.get_movie_posters(limit=80)

        # Cache the results
        if "POSTER_CACHE" not in current_app.config:
            current_app.config["POSTER_CACHE"] = {}
        current_app.config["POSTER_CACHE"][cache_key] = {
            "data": poster_urls,
            "timestamp": time.time(),
        }

        return jsonify(poster_urls)

    except Exception as e:
        import logging

        logging.warning(f"Failed to fetch cinema posters: {e}")
        return jsonify([])


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
        from app.services.expiry import calculate_user_expiry
        from app.services.invites import mark_server_used
        from app.services.media.service import get_client_for_media_server

        # Calculate expiry will be done per-server to allow server-specific expiry

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

                # Calculate server-specific expiry for this user
                user_expires = calculate_user_expiry(invitation, srv.id)

                # store local DB row with proper expiry
                new_user = User()
                new_user.username = username
                new_user.email = email
                new_user.token = uid
                new_user.code = code
                new_user.server_id = srv.id
                new_user.expires = user_expires  # Set expiry based on invitation duration (server-specific)
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

    # Server-side image cache
    import hashlib
    import time

    from flask import current_app

    # Create cache key from URL
    cache_key = f"img_{hashlib.md5(url.encode()).hexdigest()}"
    cache_duration = 3600  # 1 hour

    # Check cache first
    cached_data = current_app.config.get("IMAGE_CACHE", {})
    cached_entry = cached_data.get(cache_key)

    if cached_entry and (time.time() - cached_entry["timestamp"]) < cache_duration:
        resp = Response(cached_entry["data"], content_type=cached_entry["content_type"])
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp

    try:
        r = requests.get(url, timeout=5, stream=True)  # Reduced timeout from 10s to 5s
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "image/jpeg")
        image_data = r.content

        # Cache the image data
        if "IMAGE_CACHE" not in current_app.config:
            current_app.config["IMAGE_CACHE"] = {}
        current_app.config["IMAGE_CACHE"][cache_key] = {
            "data": image_data,
            "content_type": content_type,
            "timestamp": time.time(),
        }

        # Clean up old cache entries (simple LRU)
        if len(current_app.config["IMAGE_CACHE"]) > 200:  # Keep max 200 images
            oldest_key = min(
                current_app.config["IMAGE_CACHE"].keys(),
                key=lambda k: current_app.config["IMAGE_CACHE"][k]["timestamp"],
            )
            del current_app.config["IMAGE_CACHE"][oldest_key]

        resp = Response(image_data, content_type=content_type)
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp
    except Exception:
        return Response(status=502)
