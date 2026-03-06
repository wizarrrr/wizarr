from flask import (
    Blueprint,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from app.extensions import db
from app.models import Notification
from app.services.notifications import (  # your existing helpers
    _apprise,
    _discord,
    _notifiarr,
    _ntfy,
    _smtp,
)

notify_bp = Blueprint("notify", __name__, url_prefix="/settings/notifications")


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_form_data(form_data) -> dict:
    events = []
    if form_data.get("event_user_joined"):
        events.append("user_joined")
    if form_data.get("event_update_available"):
        events.append("update_available")
    if form_data.get("event_user_created_confirmation"):
        events.append("user_created_confirmation")
    if form_data.get("event_user_expired_notification"):
        events.append("user_expired_notification")
    if form_data.get("event_user_manually_deleted_notification"):
        events.append("user_manually_deleted_notification")
    if form_data.get("event_user_manually_disabled_notification"):
        events.append("user_manually_disabled_notification")

    service_type = form_data.get("notification_service")

    return {
        "name": form_data.get("name"),
        "url": form_data.get("url"),
        "type": service_type,
        "username": form_data.get("username") or None,
        "password": form_data.get("password") or None,
        "channel_id": _parse_int(form_data.get("channel_id")),
        "smtp_port": _parse_int(form_data.get("smtp_port")),
        "smtp_from_email": form_data.get("smtp_from_email") or None,
        "smtp_to_emails": form_data.get("smtp_to_emails") or None,
        "smtp_encryption": form_data.get("smtp_encryption") or None,
        "notification_events": ",".join(events)
        if events
        else "user_joined,update_available",
    }


def _test_connection(form: dict) -> tuple[bool, str | None]:
    service_type = form.get("type")
    url = form.get("url")

    if service_type == "discord":
        ok = _discord("Wizarr test message", url, "Test Notification") if url else False
        return ok, None
    if service_type == "ntfy":
        ok = (
            _ntfy(
                "Wizarr test message",
                "Wizarr",
                "tada",
                url,
                form["username"],
                form["password"],
            )
            if url
            else False
        )
        return ok, None
    if service_type == "apprise":
        ok = _apprise("Wizarr test message", "Wizarr", "tada", url) if url else False
        return ok, None
    if service_type == "notifiarr":
        channel_id = form.get("channel_id")
        if url and channel_id:
            ok = _notifiarr(
                "Connection established. You will now receive notifications in this channel.",
                "Test successful!",
                url,
                channel_id,
            )
            return ok, None
        return False, "Notifiarr requires both URL and channel ID."
    if service_type == "smtp":
        if not url:
            return False, "SMTP host is required."
        return _smtp(
            "Wizarr test message",
            "Wizarr Test Notification",
            url,
            form.get("smtp_port"),
            form.get("username"),
            form.get("password"),
            form.get("smtp_from_email"),
            form.get("smtp_to_emails"),
            form.get("smtp_encryption"),
            return_error=True,
        )

    return False, "Unsupported notification service."


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
        form = _build_form_data(request.form)
        ok, error_message = _test_connection(form)

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
                error=error_message or "Could not connect – check URL / credentials.",
            )
        )
        resp.headers["HX-Retarget"] = "#create-modal"
        return resp

    # GET → just render the modal
    return render_template("modals/create-notification-agent.html")


@notify_bp.route("/edit/<int:agent_id>", methods=["GET", "POST"])
@login_required
def edit(agent_id):
    agent = db.get_or_404(Notification, agent_id)

    if request.method == "POST":
        form = _build_form_data(request.form)
        ok, error_message = _test_connection(form)

        if ok:
            # Update the agent with new values
            agent.name = form["name"]
            agent.url = form["url"]
            agent.type = form["type"]
            agent.username = form["username"]
            agent.password = form["password"]
            agent.channel_id = form["channel_id"]
            agent.smtp_port = form["smtp_port"]
            agent.smtp_from_email = form["smtp_from_email"]
            agent.smtp_to_emails = form["smtp_to_emails"]
            agent.smtp_encryption = form["smtp_encryption"]
            agent.notification_events = form["notification_events"]
            db.session.commit()
            return redirect(url_for(".list_agents"))

        # on failure, re-render the HTMX modal with an error
        resp = make_response(
            render_template(
                "modals/edit-notification-agent.html",
                agent=agent,
                error=error_message or "Could not connect – check URL / credentials.",
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
