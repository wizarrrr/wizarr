from flask import Blueprint, make_response, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Notification
from app.services.notifications import (  # your existing helpers
    _apprise,
    _discord,
    _notifiarr,
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
        # Collect selected events from checkboxes
        events = []
        if request.form.get("event_user_joined"):
            events.append("user_joined")
        if request.form.get("event_update_available"):
            events.append("update_available")

        form = {
            "name": request.form.get("name"),
            "url": request.form.get("url"),
            "type": request.form.get("notification_service"),
            "username": request.form.get("username") or None,
            "password": request.form.get("password") or None,
            "channel_id": request.form.get("channel_id") or None,
            "notification_events": ",".join(events)
            if events
            else "user_joined,update_available",
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
        elif form["type"] == "notifiarr":
            url = form.get("url")
            channel_id_raw = form.get("channel_id")

            if url and channel_id_raw:
                channel_id = int(channel_id_raw)
                ok = _notifiarr(
                    "Connection established. You will now receive notifications in this channel.",
                    "Test successful!",
                    url,
                    channel_id,
                )

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


@notify_bp.route("/edit/<int:agent_id>", methods=["GET", "POST"])
@login_required
def edit(agent_id):
    agent = Notification.query.get_or_404(agent_id)

    if request.method == "POST":
        # Collect selected events from checkboxes
        events = []
        if request.form.get("event_user_joined"):
            events.append("user_joined")
        if request.form.get("event_update_available"):
            events.append("update_available")

        form = {
            "name": request.form.get("name"),
            "url": request.form.get("url"),
            "type": request.form.get("notification_service"),
            "username": request.form.get("username") or None,
            "password": request.form.get("password") or None,
            "channel_id": request.form.get("channel_id") or None,
            "notification_events": ",".join(events)
            if events
            else "user_joined,update_available",
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
        elif form["type"] == "notifiarr":
            url = form.get("url")
            channel_id_raw = form.get("channel_id")

            if url and channel_id_raw:
                channel_id = int(channel_id_raw)
                ok = _notifiarr(
                    "Connection established. You will now receive notifications in this channel.",
                    "Test successful!",
                    url,
                    channel_id,
                )

        if ok:
            # Update the agent with new values
            agent.name = form["name"]
            agent.url = form["url"]
            agent.type = form["type"]
            agent.username = form["username"]
            agent.password = form["password"]
            agent.channel_id = form["channel_id"]
            agent.notification_events = form["notification_events"]
            db.session.commit()
            return redirect(url_for(".list_agents"))

        # on failure, re-render the HTMX modal with an error
        resp = make_response(
            render_template(
                "modals/edit-notification-agent.html",
                agent=agent,
                error="Could not connect – check URL / credentials.",
            )
        )
        resp.headers["HX-Retarget"] = "#create-modal"
        return resp

    # GET → just render the modal
    return render_template("modals/edit-notification-agent.html", agent=agent)


@notify_bp.route("/", methods=["DELETE"])
@login_required
def delete_agent():
    agent_id = request.args.get("delete")
    if agent_id:
        # replace peewee delete().where(...).execute()
        (Notification.query.filter_by(id=agent_id).delete(synchronize_session=False))
        db.session.commit()
    return "", 204
