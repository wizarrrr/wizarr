from flask import Blueprint, make_response, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Notification
from app.services.notifications import (  # your existing helpers
    _apprise,
    _discord,
    _ntfy,
)

notify_bp = Blueprint("notify", __name__, url_prefix="/settings/notifications")


@notify_bp.route("/", methods=["GET"])
@login_required
def list_agents():
    # replace peewee .select() with SQLAlchemy .query.all()
    agents = Notification.query.all()
    return render_template("settings/notifications.html", agents=agents)


@notify_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        form = {
            "name": request.form.get("name"),
            "url": request.form.get("url"),
            "type": request.form.get("notification_service"),
            "username": request.form.get("username") or None,
            "password": request.form.get("password") or None,
        }

        # test the connection
        ok = False
        if form["type"] == "discord":
            url = form.get("url")
            if url:
                ok = _discord("Wizarr test message", url)
        elif form["type"] == "ntfy":
            url = form.get("url")
            if url:
                ok = _ntfy(
                    "Wizarr test message",
                    "Wizarr",
                    "tada",
                    url,
                    form["username"],
                    form["password"],
                )
        elif form["type"] == "apprise":
            url = form.get("url")
            if url:
                ok = _apprise("Wizarr test message", "Wizarr", "tada", url)

        if ok:
            # from Notification.create(**form) to SQLAlchemy ORM
            agent = Notification(**form)
            db.session.add(agent)
            db.session.commit()
            return redirect(url_for(".list_agents"))

        # on failure, re-render the HTMX modal with an error
        resp = make_response(
            render_template(
                "modals/create-notification-agent.html",
                error="Could not connect – check URL / credentials.",
            )
        )
        resp.headers["HX-Retarget"] = "#create-modal"
        return resp

    # GET → just render the modal
    return render_template("modals/create-notification-agent.html")


@notify_bp.route("/", methods=["DELETE"])
@login_required
def delete_agent():
    agent_id = request.args.get("delete")
    if agent_id:
        # replace peewee delete().where(...).execute()
        (Notification.query.filter_by(id=agent_id).delete(synchronize_session=False))
        db.session.commit()
    return "", 204
