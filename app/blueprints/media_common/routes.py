"""Common media server routes that can be reused across all media types.

This module provides factory functions to create standardized routes for
different media server types, eliminating code duplication.
"""

from flask import Blueprint, abort, jsonify, redirect, render_template, request
from flask_login import login_required

from app.forms.join import JoinForm
from app.services.invitation_manager import InvitationManager, LibraryScanner


def create_media_blueprint(server_type: str, url_prefix: str) -> Blueprint:
    """Create a standardized blueprint for a media server type.

    Args:
        server_type: The server type (e.g., 'jellyfin', 'emby')
        url_prefix: URL prefix for the blueprint (e.g., '/jf', '/emby')

    Returns:
        Blueprint: Configured blueprint with standard routes
    """
    bp = Blueprint(server_type, __name__, url_prefix=url_prefix)

    @bp.route("/scan", methods=["POST"])
    @login_required
    def scan():
        """Scan libraries with arbitrary credentials."""
        url = request.args.get("url") or request.args.get(f"{server_type}_url")
        key = request.args.get("api_key") or request.args.get(f"{server_type}_api_key")

        if not url or not key:
            abort(400)

        success, libraries = LibraryScanner.scan_with_credentials(server_type, url, key)

        if success:
            return jsonify(libraries)
        abort(400)
        return None

    @bp.route("/scan-specific", methods=["POST"])
    @login_required
    def scan_specific():
        """Scan libraries with saved credentials."""
        success, libraries = LibraryScanner.scan_with_saved_credentials(server_type)

        if success:
            return jsonify(libraries)
        abort(400)
        return None

    @bp.route("/join", methods=["POST"])
    def public_join():
        """Public join endpoint called from the wizard form."""
        form = JoinForm()
        error = None

        if form.validate_on_submit():
            success, redirect_code, errors = InvitationManager.process_invitation(
                code=form.code.data or "",
                username=form.username.data or "",
                password=form.password.data or "",
                confirm_password=form.confirm_password.data or "",
                email=form.email.data or "",
            )

            if success:
                redirect_url = InvitationManager.handle_successful_join(
                    redirect_code or ""
                )
                return redirect(redirect_url)
            error = "; ".join(errors)

        return render_template(
            "welcome-jellyfin.html",
            form=form,
            server_type=server_type,
            error=error,
        )

    return bp


def register_media_blueprints(app):
    """Register all media server blueprints with the Flask app.

    Args:
        app: Flask application instance
    """
    media_configs = [
        ("jellyfin", "/jf"),
        ("emby", "/emby"),
        ("audiobookshelf", "/abs"),
        ("kavita", "/kavita"),
        ("komga", "/komga"),
        ("romm", "/romm"),
    ]

    for server_type, url_prefix in media_configs:
        bp = create_media_blueprint(server_type, url_prefix)
        app.register_blueprint(bp)
