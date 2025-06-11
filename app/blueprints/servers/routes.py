from flask import Blueprint, render_template, request, redirect, make_response, url_for
from flask_login import login_required
from app.extensions import db
from app.models import MediaServer
from app.services.servers import check_plex, check_jellyfin

servers_bp = Blueprint("servers", __name__, url_prefix="/settings/servers")

@servers_bp.route("/", methods=["GET"])
@login_required
def list_servers():
    servers = MediaServer.query.all()
    return render_template("settings/servers.html", servers=servers)


def _check(data: dict) -> tuple[bool, str]:
    stype = data.get("server_type")
    if stype == "plex":
        return check_plex(data.get("server_url"), data.get("api_key"))
    return check_jellyfin(data.get("server_url"), data.get("api_key"))


@servers_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        form = {
            "server_name": request.form.get("server_name"),
            "server_url": request.form.get("server_url"),
            "server_type": request.form.get("server_type"),
            "api_key": request.form.get("api_key"),
        }
        ok, err = _check(form)
        if ok:
            server = MediaServer(**form)
            db.session.add(server)
            db.session.commit()
            return redirect(url_for(".list_servers"))
        resp = make_response(render_template(
            "modals/create-media-server.html",
            error=err,
        ))
        resp.headers["HX-Retarget"] = "#create-modal"
        return resp

    return render_template("modals/create-media-server.html")


@servers_bp.route("/", methods=["DELETE"])
@login_required
def delete_server():
    sid = request.args.get("delete")
    if sid:
        MediaServer.query.filter_by(id=sid).delete(synchronize_session=False)
        db.session.commit()
    return "", 204
