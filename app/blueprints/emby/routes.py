from flask import Blueprint, request, jsonify, abort, render_template, redirect
from flask_login import login_required
import logging
import datetime

# Import models needed for routes
from app.models import User, Invitation, Library

# Import the EmbyClient and all helper functions from the service module
from app.services.media.emby import EmbyClient
from app.forms.join import JoinForm

emby_bp = Blueprint("emby", __name__, url_prefix="/emby")

# Ajax scan with arbitrary creds
@emby_bp.route("/scan", methods=["POST"])
@login_required
def scan():
    client = EmbyClient()
    url = request.args.get("emby_url")
    key = request.args.get("emby_api_key")
    if not url or not key:
        abort(400)
    try:
        libs = client.libraries()
        return jsonify(libs)
    except Exception as e:
        logging.error(f"Error scanning Emby libraries: {str(e)}")
        abort(400)

# Scan with saved creds
@emby_bp.route("/scan-specific", methods=["POST"])
@login_required
def scan_specific():
    client = EmbyClient()
    return jsonify(client.libraries())

# The join function is now defined in app.services.media.emby

# Public join endpoint called from the wizard form
@emby_bp.route("/join", methods=["POST"])
def public_join():
    form = JoinForm()
    if form.validate_on_submit():
        client = EmbyClient()
        ok, msg = client.join(
            username=form.username.data,
            password=form.password.data,
            confirm=form.confirm_password.data,
            email=form.email.data,
            code=form.code.data,
        )
        if ok:
            return redirect("/wizard/")
        error = msg
    else:
        error = None
    return render_template(
        "welcome-jellyfin.html",
        form=form,
        server_type="emby",
        error=error,
    )
