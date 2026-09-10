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
    _telegram,
    _webhook,
    is_webhook_url_allowed,
)

notify_bp = Blueprint("notify", __name__, url_prefix="/settings/notifications")


def _test_agent(form: dict) -> tuple[bool, str | None]:
    """Send a test notification for a form-submitted agent config.

    Returns (ok, error_message). A None error_message means the test failed
    but there's no more specific reason to show the user beyond the generic
    "could not connect" fallback.
    """
    url = form.get("url")
    if not url:
        return False, "URL is required."

    t = form["type"]
    if t == "discord":
        return _discord("Wizarr test message", url, "Test Notification"), None
    if t == "ntfy":
        return (
            _ntfy(
                "Wizarr test message",
                "Wizarr",
                "tada",
                url,
                form["username"],
                form["password"],
            ),
            None,
        )
    if t == "apprise":
        return _apprise("Wizarr test message", "Wizarr", "tada", url), None
    if t == "notifiarr":
        raw = form.get("channel_id")
        if not raw:
            return False, "Channel ID is required for Notifiarr."
        return (
            _notifiarr(
                "Connection established. You will now receive notifications in this channel.",
                "Test successful!",
                url,
                int(raw),
            ),
            None,
        )
    if t == "telegram":
        if not (form.get("telegram_bot_token") and form.get("telegram_chat_id")):
            return False, "Telegram bot token and chat id are required."
        return (
            _telegram(
                "Wizarr test message",
                "Wizarr",
                url,
                form["telegram_bot_token"],
                form["telegram_chat_id"],
            ),
            None,
        )
    if t == "webhook":
        if not is_webhook_url_allowed(url):
            return False, (
                "Webhook URL must use https, or http on a loopback host "
                "(localhost, 127.0.0.1, host.docker.internal)."
            )
        ok = _webhook(
            url,
            form.get("webhook_secret"),
            "test",
            "Wizarr test message",
            "This is a test delivery from Wizarr.",
            {"test": True},
            bool(form.get("include_password")),
        )
        return ok, None
    return False, "Unknown notification service."


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
            "telegram_bot_token": request.form.get("telegram_bot_token") or None,
            "telegram_chat_id": request.form.get("telegram_chat_id") or None,
            "webhook_secret": request.form.get("webhook_secret") or None,
            "include_password": bool(request.form.get("include_password")),
            "notification_events": ",".join(events)
            if events
            else "user_joined,update_available",
        }

        ok, error = _test_agent(form)

        if ok:
            agent = Notification(**form)
            db.session.add(agent)
            db.session.commit()
            return redirect(url_for(".list_agents"))

        # on failure, re-render the HTMX modal with an error
        resp = make_response(
            render_template(
                "modals/create-notification-agent.html",
                error=error or "Could not connect – check URL / credentials.",
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
            "telegram_bot_token": request.form.get("telegram_bot_token") or None,
            "telegram_chat_id": request.form.get("telegram_chat_id") or None,
            "webhook_secret": request.form.get("webhook_secret") or None,
            "include_password": bool(request.form.get("include_password")),
            "notification_events": ",".join(events)
            if events
            else "user_joined,update_available",
        }

        ok, error = _test_agent(form)

        if ok:
            agent.name = form["name"]
            agent.url = form["url"]
            agent.type = form["type"]
            agent.username = form["username"]
            agent.password = form["password"]
            agent.channel_id = form["channel_id"]
            agent.telegram_bot_token = form["telegram_bot_token"]
            agent.telegram_chat_id = form["telegram_chat_id"]
            agent.webhook_secret = form["webhook_secret"]
            agent.include_password = form["include_password"]
            agent.notification_events = form["notification_events"]
            db.session.commit()
            return redirect(url_for(".list_agents"))

        # on failure, re-render the HTMX modal with an error
        resp = make_response(
            render_template(
                "modals/edit-notification-agent.html",
                agent=agent,
                error=error or "Could not connect – check URL / credentials.",
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
