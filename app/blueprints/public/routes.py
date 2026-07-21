from datetime import UTC, datetime, timedelta
import os
import secrets
from pathlib import Path

import requests
import structlog
from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_babel import gettext as _

from app.extensions import db, limiter
from app.models import ExternalEnrollmentState, Invitation, MediaServer, Settings, User
from app.services.external_enrollment.providers import (
    ExternalEnrollmentContext,
    build_external_enrollment_url,
)
from app.services.invites import is_invite_valid
from app.services.media.plex import PlexInvitationError, handle_oauth_token

public_bp = Blueprint("public", __name__)


def utc_now_naive() -> datetime:
    """Return naive UTC for SQLite-compatible datetime comparisons."""
    return datetime.now(UTC).replace(tzinfo=None)


def _media_permission_flags(invitation: Invitation, server: MediaServer) -> dict:
    return {
        "allow_downloads": bool(getattr(invitation, "allow_downloads", False))
        or bool(getattr(server, "allow_downloads", False)),
        "allow_live_tv": bool(getattr(invitation, "allow_live_tv", False))
        or bool(getattr(server, "allow_live_tv", False)),
        "allow_mobile_uploads": bool(getattr(invitation, "allow_mobile_uploads", False))
        or bool(getattr(server, "allow_mobile_uploads", False)),
    }


def _apply_safe_media_user_policy(
    client, user_id: str, invitation: Invitation, server: MediaServer
) -> dict:
    permissions = _media_permission_flags(invitation, server)
    current_policy = client.get(f"/Users/{user_id}").json().get("Policy", {})
    current_policy.update(
        {
            "IsAdministrator": False,
            "EnableContentDeletion": False,
            "EnableContentDeletionFromFolders": [],
            "EnableContentDownloading": permissions["allow_downloads"],
            "EnableLiveTvAccess": permissions["allow_live_tv"],
            "EnableLiveTvManagement": False,
            "AllowCameraUpload": permissions["allow_mobile_uploads"],
            "EnablePublicSharing": False,
            "AllowSharingPersonalItems": False,
            "EnableSubtitleManagement": False,
            "EnableRemoteControlOfOtherUsers": False,
        }
    )

    max_sessions = getattr(invitation, "max_active_sessions", None)
    if server.server_type == "jellyfin" and max_sessions is not None:
        current_policy["MaxActiveSessions"] = max_sessions

    client.set_policy(user_id, current_policy)
    return permissions


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


# ─── External enrollment start ───────────────────────────────────────────────
@public_bp.route("/invitation/external/start/<code>")
@limiter.limit("20 per minute")
def start_external_enrollment(code):
    """Start external account enrollment for an invitation."""
    valid, msg = is_invite_valid(code)
    if not valid:
        abort(404, description=msg)

    invitation = Invitation.query.filter(
        db.func.lower(Invitation.code) == code.lower()
    ).first()
    if not invitation:
        abort(404, description="Invalid code")

    if (invitation.account_creation_mode or "wizarr") != "external":
        abort(400, description="Invitation is not configured for external enrollment")

    state = secrets.token_urlsafe(32)
    callback_url = url_for(
        "public.external_enrollment_callback",
        _external=True,
    )

    context = ExternalEnrollmentContext(
        invite_code=invitation.code,
        state=state,
        callback_url=callback_url,
    )

    try:
        enrollment_url = build_external_enrollment_url(invitation, context)
    except ValueError as exc:
        session.pop("external_enrollment_state", None)
        abort(400, description=str(exc))

    pending = ExternalEnrollmentState(
        invitation=invitation,
        state=state,
        provider=invitation.external_enrollment_provider or "static_url",
        callback_url=callback_url,
        expires_at=utc_now_naive() + timedelta(minutes=30),
    )

    db.session.add(pending)
    db.session.commit()

    # Optional convenience/debug state. DB is now source of truth.
    session["external_enrollment_state"] = state

    return redirect(enrollment_url)


def _get_external_enrollment_header_config(key: str) -> str | None:
    """Get an external enrollment header name from app config or environment."""
    return current_app.config.get(key) or os.environ.get(key)


def _get_external_enrollment_subject() -> str | None:
    """Get the externally authenticated subject from a trusted proxy header."""
    auth_header = _get_external_enrollment_header_config(
        "EXTERNAL_ENROLLMENT_AUTH_HEADER"
    )
    if not auth_header:
        abort(400, description="External enrollment auth header is not configured")

    return request.headers.get(auth_header)


# ─── External enrollment callback ────────────────────────────────────────────
@public_bp.route("/invitation/external/callback")
@limiter.limit("20 per minute")
def external_enrollment_callback():
    """Resume the Wizarr wizard after external account enrollment."""
    provided_state = request.args.get("state")
    if not provided_state:
        abort(400, description="Missing external enrollment state")

    pending = ExternalEnrollmentState.query.filter_by(
        state=provided_state,
        consumed_at=None,
    ).first()

    if not pending:
        abort(400, description="Invalid or expired external enrollment state")

    now = utc_now_naive()

    if pending.expires_at < now:
        pending.consumed_at = now
        db.session.commit()
        session.pop("external_enrollment_state", None)
        abort(400, description="Invalid or expired external enrollment state")

    external_subject = _get_external_enrollment_subject()
    if not external_subject:
        abort(403, description="External enrollment authentication was not verified")

    invitation = pending.invitation
    if not invitation:
        pending.consumed_at = now
        db.session.commit()
        session.pop("external_enrollment_state", None)
        abort(404, description="Invalid code")

    valid, msg = is_invite_valid(invitation.code)
    if not valid:
        pending.consumed_at = now
        db.session.commit()
        session.pop("external_enrollment_state", None)
        abort(404, description=msg)

    if (invitation.account_creation_mode or "wizarr") != "external":
        pending.consumed_at = now
        db.session.commit()
        session.pop("external_enrollment_state", None)
        abort(400, description="Invitation is not configured for external enrollment")

    pending.external_subject = external_subject
    pending.consumed_at = now

    session["wizard_access"] = invitation.code
    session["invitation_in_progress"] = True
    session["external_enrollment_user"] = {
        "subject": external_subject,
    }

    if invitation.wizard_bundle_id:
        session["wizard_bundle_id"] = invitation.wizard_bundle_id
    else:
        session.pop("wizard_bundle_id", None)

    session.pop("external_enrollment_state", None)

    db.session.commit()

    return redirect(url_for("wizard.post_wizard", idx=0))


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
                structlog.get_logger().error(
                    "Plex invitation failed",
                    code=code,
                    error=e.message,
                )
                name_setting = Settings.query.filter_by(key="server_name").first()
                server_name = name_setting.value if name_setting else None

                return render_template(
                    "user-plex-login.html",
                    server_name=server_name,
                    code=code,
                    code_error=_(
                        "There was an issue setting up your access. Please contact your server admin."
                    ),
                )
            except Exception as e:
                structlog.get_logger().error(
                    "Unexpected error during Plex OAuth",
                    code=code,
                    error=str(e),
                )
                name_setting = Settings.query.filter_by(key="server_name").first()
                server_name = name_setting.value if name_setting else None

                return render_template(
                    "user-plex-login.html",
                    server_name=server_name,
                    code=code,
                    code_error=_(
                        "There was an issue setting up your access. Please contact your server admin."
                    ),
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
        from app.services.invitation_flow.workflows import _get_server_colors

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
        colors = _get_server_colors(server_type)
        return render_template(
            "welcome-jellyfin.html",
            code=code,
            server_type=server_type,
            server_name=server_name,
            gradient_start=colors["gradient_start"],
            gradient_end=colors["gradient_end"],
            shadow_color=colors["shadow_color"],
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
        Path(current_app.root_path) / "static",
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

        # Determine username and email for all account creations
        if plex_user:
            username = plex_user.username
            email = plex_user.email
        else:
            # For non-Plex flows, use form data or generate a unique username
            import uuid

            username = request.form.get("username") or f"user-{uuid.uuid4().hex[:8]}"
            email = request.form.get("email") or ""

        # Create LDAP user if configured
        from app.services.ldap.invitation_ldap import InvitationLDAPHandler

        ldap_handler = InvitationLDAPHandler(invitation)
        is_ldap_user = False

        if ldap_handler.should_create_ldap_user():
            ldap_success, ldap_result = ldap_handler.create_ldap_user(
                username=username,
                email=email,
                password=pw,
            )

            if not ldap_success:
                return render_template(
                    "choose-password.html",
                    code=code,
                    error=f"Failed to create LDAP user: {ldap_result}",
                )

            # Mark that this is an LDAP user
            is_ldap_user = True

        # Provision accounts on remaining servers
        from app.services.expiry import calculate_user_expiry
        from app.services.invites import mark_server_used
        from app.services.media.service import get_client_for_media_server

        # Calculate expiry will be done per-server to allow server-specific expiry

        for srv in invitation.servers:
            if srv.server_type == "plex":
                continue  # already done

            client = get_client_for_media_server(srv)

            try:
                permissions = _media_permission_flags(invitation, srv)
                if srv.server_type in ("jellyfin", "emby"):
                    uid = client.create_user(username, pw)
                    permissions = _apply_safe_media_user_policy(
                        client, uid, invitation, srv
                    )
                elif srv.server_type in ("audiobookshelf", "romm"):
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
                new_user.is_ldap_user = is_ldap_user
                new_user.is_admin = False
                new_user.allow_downloads = permissions["allow_downloads"]
                new_user.allow_live_tv = permissions["allow_live_tv"]
                new_user.allow_camera_upload = permissions["allow_mobile_uploads"]
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
    """
    Secure image proxy using opaque tokens instead of URLs.

    This prevents SSRF attacks by not exposing the underlying URL.
    Only accepts signed tokens generated by ImageProxyService.
    """
    from app.services.image_proxy import ImageProxyService

    token = request.args.get("token")
    if not token:
        return Response(status=400)

    # Check image cache first
    cached_image = ImageProxyService.get_cached_image(token)
    if cached_image:
        resp = Response(cached_image["data"], content_type=cached_image["content_type"])
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp

    # Validate token and get URL
    mapping = ImageProxyService.validate_token(token)
    if not mapping:
        return Response(status=403)  # Invalid or expired token

    url = mapping["url"]
    server_id = mapping.get("server_id")

    try:
        # Prepare headers for authenticated requests (cached per server)
        headers = ImageProxyService.get_server_headers(server_id).copy()

        # Fetch the image using a pooled session to reuse TCP/TLS handshakes
        session = ImageProxyService.get_session(url, server_id)
        r = session.get(url, headers=headers, timeout=(5, 15))
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "image/jpeg")
        image_data = r.content

        # Cache the image
        ImageProxyService.cache_image(token, image_data, content_type)

        resp = Response(image_data, content_type=content_type)
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp

    except requests.RequestException:
        return Response(status=502)
    except Exception:
        return Response(status=502)


# ─── Password Reset ──────────────────────────────────────────────────────────
@public_bp.route("/reset/<code>", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def reset_password(code):
    """Handle password reset via token link."""
    from app.services.password_reset import get_reset_token, use_reset_token

    # Validate the reset token
    token, error = get_reset_token(code)

    if not token:
        return render_template("password-reset-error.html", error=error, code=code)

    # GET request - show the password reset form
    if request.method == "GET":
        return render_template(
            "password-reset-form.html",
            code=code,
            username=token.user.username,
            expires_at=token.expires_at,
        )

    # POST request - process the password reset
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    # Validate passwords match
    if new_password != confirm_password:
        return render_template(
            "password-reset-form.html",
            code=code,
            username=token.user.username,
            expires_at=token.expires_at,
            error="Passwords do not match",
        )

    # Validate password length
    if not (8 <= len(new_password) <= 128):
        return render_template(
            "password-reset-form.html",
            code=code,
            username=token.user.username,
            expires_at=token.expires_at,
            error="Password must be between 8 and 128 characters",
        )

    # Use the reset token to change the password
    success, message = use_reset_token(code, new_password)

    if success:
        return render_template(
            "password-reset-success.html", username=token.user.username
        )
    return render_template(
        "password-reset-form.html",
        code=code,
        username=token.user.username,
        expires_at=token.expires_at,
        error=message,
    )
