from flask import Blueprint, request, jsonify, abort, render_template, redirect, session
from flask_login import login_required

from app.services.media.audiobookshelf import AudiobookshelfClient
from app.forms.join import JoinForm
from app.models import Invitation, MediaServer
from app.services.media.service import get_client_for_media_server

abs_bp = Blueprint("audiobookshelf", __name__, url_prefix="/abs")

# Ajax scan with arbitrary creds (optional)
@abs_bp.route("/scan", methods=["POST"])
@login_required
def scan():
    client = AudiobookshelfClient()
    url = request.args.get("url")
    key = request.args.get("api_key")
    if not url or not key:
        abort(400)
    try:
        hdrs = {"Authorization": f"Bearer {key}"}
        libs_resp = client._get("/api/libraries")  # type: ignore  # internal use
        libs = libs_resp.json().get("libraries", [])
        return jsonify({lib["name"]: lib["id"] for lib in libs})
    except Exception:
        abort(400)

# Public join endpoint called from the wizard form
@abs_bp.route("/join", methods=["POST"])
def public_join():
    form = JoinForm()
    if form.validate_on_submit():
        inv = Invitation.query.filter_by(code=form.code.data).first()
        server = inv.server if inv else MediaServer.query.first()
        client = get_client_for_media_server(server)
        ok, msg = client.join(
            username=form.username.data,
            password=form.password.data,
            confirm=form.confirm_password.data,
            email=form.email.data,
            code=form.code.data,
        )
        if ok:
            session["wizard_access"] = form.code.data
            return redirect("/wizard/")
        error = msg
    else:
        error = None
    return render_template(
        "welcome-jellyfin.html",  # reuse same template
        form=form,
        server_type="audiobookshelf",
        error=error,
    ) 