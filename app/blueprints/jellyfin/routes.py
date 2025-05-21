from flask import Blueprint, request, jsonify, abort, render_template, redirect
from flask_login import login_required
from app.services.jellyfin_client   import JellyfinClient
from app.services.jellyfin_workflow import join


jellyfin_bp = Blueprint("jellyfin", __name__, url_prefix="/jf")

# Ajax scan with arbitrary creds
@jellyfin_bp.route("/scan", methods=["POST"])
@login_required
def scan():
    client = JellyfinClient()
    url  = request.args.get("jellyfin_url")
    key  = request.args.get("jellyfin_api_key")
    if not url or not key:
        abort(400)
    try:
        libs = {i["Name"]: i["Id"]
                for i in client.get("/Library/MediaFolders").json()["Items"]}
        return jsonify(libs)
    except Exception:
        abort(400)

# Scan with saved creds
@jellyfin_bp.route("/scan-specific", methods=["POST"])
@login_required
def scan_specific():
    client = JellyfinClient()
    return jsonify(client.libraries())

# Public join endpoint called from the wizard form
@jellyfin_bp.route("/join", methods=["POST"])
def public_join():
    client = JellyfinClient()
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
                           error=msg)
