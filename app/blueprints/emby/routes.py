from flask import Blueprint, request, jsonify, abort, render_template, redirect
from flask_login import login_required
import logging
import datetime

# Import models needed for routes
from app.models import User, Invitation, Library

# Import the EmbyClient and all helper functions from the service module
from app.services.media.emby import EmbyClient, join, mark_invite_used, folder_name_to_id, set_specific_folders

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
    ok, msg = join(
        username = request.form["username"],
        password = request.form["password"],
        confirm  = request.form["confirm-password"],
        email    = request.form["email"],
        code     = request.form["code"],
    )
    if ok:
        return redirect("/wizard/")
    return render_template("welcome-jellyfin.html",
                          username=request.form["username"],
                          email=request.form["email"],
                          code=request.form["code"],
                          server_type="emby",
                          error=msg)
