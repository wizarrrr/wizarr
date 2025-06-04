from flask import Blueprint, request, jsonify, abort, render_template, redirect
from flask_login import login_required
from app.services.media.jellyfin import JellyfinClient
from app.forms.join import JoinForm


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
    form = JoinForm()
    if form.validate_on_submit():
        client = JellyfinClient()
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
        server_type="jellyfin",
        error=error,
    )
