import base64
import json
import logging
import shutil
import subprocess
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlparse

import apprise
import requests

from app.models import Notification

__all__ = ["notify"]


def _resolve_smtp_endpoint(
    host: str,
    port: int | None,
    encryption: str | None,
) -> tuple[str | None, int, str]:
    resolved_host = host.strip()
    resolved_port = port
    encryption_value = (encryption or "starttls").strip().lower()

    if encryption_value in ("tls", "starttls"):
        resolved_encryption = "starttls"
    elif encryption_value in ("ssl", "smtps", "ssl/tls"):
        resolved_encryption = "ssl"
    elif encryption_value in ("none", "plain"):
        resolved_encryption = "none"
    else:
        resolved_encryption = "starttls"

    if resolved_host.startswith(("smtp://", "smtps://")):
        parsed = urlparse(resolved_host)
        if not parsed.hostname:
            return None, 0, resolved_encryption
        resolved_host = parsed.hostname
        if parsed.port and not resolved_port:
            resolved_port = parsed.port
        if parsed.scheme == "smtps":
            resolved_encryption = "ssl"

    # Accept "host:port" if users include port in the host field.
    if ":" in resolved_host and not resolved_port and not resolved_host.startswith("["):
        host_part, port_part = resolved_host.rsplit(":", 1)
        if host_part and port_part.isdigit():
            resolved_host = host_part
            resolved_port = int(port_part)

    if resolved_encryption == "ssl":
        resolved_port = resolved_port or 465
    elif resolved_encryption == "none":
        resolved_port = resolved_port or 25
    else:
        resolved_port = resolved_port or 587

    return resolved_host or None, resolved_port, resolved_encryption


def _send(url: str, data, headers: dict) -> bool:
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=5)
        if resp.status_code in (200, 204):
            return True
        logging.error(
            "Notification failed – %s → %s • %s", url, resp.status_code, resp.text
        )
        return False
    except requests.RequestException as exc:
        logging.error("Notification request error: %s", exc)
        return False


def _discord(
    msg: str,
    webhook_url: str,
    title: str = "Wizarr Notification",
    previous_version: str | None = None,
    new_version: str | None = None,
) -> bool:
    embed = {
        "title": title,
        "description": msg,
        "author": {
            "name": "Wizarr",
            "icon_url": "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/wizarr.png",
        },
    }

    # Add version fields for update notifications
    if previous_version and new_version:
        embed["fields"] = [
            {"name": "Previous Version", "value": previous_version, "inline": True},
            {"name": "New Version", "value": new_version, "inline": True},
        ]

    data = json.dumps({"embeds": [embed]})
    headers = {"Content-Type": "application/json"}
    return _send(webhook_url, data, headers)


def _ntfy(
    msg: str,
    title: str,
    tags: str,
    url: str,
    username: str | None,
    password: str | None,
) -> bool:
    headers = {"Title": title, "Tags": tags}
    if username and password:
        creds = f"{username}:{password}"
        headers["Authorization"] = "Basic " + base64.b64encode(creds.encode()).decode()
    return _send(url, msg, headers)


def _apprise(msg: str, title: str, _tags: str, url: str) -> bool:
    try:
        apprise_client = apprise.Apprise()
        apprise_client.add(url)

        result = apprise_client.notify(title=title, body=msg)

        logging.info(f"Apprise notification {'sent' if result else 'failed'}: {title}")
        return bool(result)

    except Exception as e:
        logging.error(f"Error sending Apprise notification: {e}")
        return False


def _notifiarr(
    msg: str,
    title: str,
    url: str,
    channel_id: int,
) -> bool:
    data = json.dumps(
        {
            "notification": {"update": False, "name": "Wizarr", "event": ""},
            "discord": {
                "color": "FFFFFF",
                "ping": {"pingUser": 0, "pingRole": 0},
                "images": {"thumbnail": "", "image": ""},
                "text": {
                    "title": title,
                    "icon": "https://raw.githubusercontent.com/wizarrrr/wizarr/refs/heads/main/app/static/img/pwa-icons/icon-128x128.png",
                    "content": "",
                    "description": msg,
                    "fields": [],
                    "footer": "",
                },
                "ids": {"channel": channel_id},
            },
        }
    )
    headers = {"Content-Type": "application/json"}
    return _send(url, data, headers)


def _smtp(
    msg: str,
    title: str,
    host: str,
    port: int | None,
    username: str | None,
    password: str | None,
    from_email: str | None,
    to_emails: str | None,
    encryption: str | None,
    html_message: str | None = None,
    return_error: bool = False,
) -> bool | tuple[bool, str | None]:
    def _result(ok: bool, error: str | None = None):
        return (ok, error) if return_error else ok

    if not host or not from_email or not to_emails:
        error_message = "Missing host, from address, or recipient emails."
        logging.error("SMTP notification missing host/from/to configuration")
        return _result(False, error_message)

    resolved_host, resolved_port, resolved_encryption = _resolve_smtp_endpoint(
        host,
        port,
        encryption,
    )

    if not resolved_host:
        error_message = f"SMTP host is invalid: {host}"
        logging.error("SMTP notification host is invalid: %s", host)
        return _result(False, error_message)

    recipients = [email.strip() for email in to_emails.split(",") if email.strip()]
    if not recipients:
        error_message = "SMTP notification requires at least one recipient."
        logging.error("SMTP notification requires at least one recipient")
        return _result(False, error_message)

    node_executable = shutil.which("node")
    if not node_executable:
        error_message = "Node.js is required for SMTP notifier but was not found."
        logging.error("Node.js is required for SMTP notifier but was not found")
        return _result(False, error_message)

    script_path = Path(__file__).resolve().parents[2] / "scripts" / "smtp_notifier.mjs"
    if not script_path.exists():
        error_message = "SMTP notifier script is missing."
        logging.error("SMTP notifier script not found: %s", script_path)
        return _result(False, error_message)

    payload = {
        "host": resolved_host,
        "port": resolved_port,
        "encryption": resolved_encryption,
        "username": username,
        "password": password,
        "fromEmail": from_email,
        "toEmails": recipients,
        "title": title,
        "message": msg,
        "htmlMessage": html_message,
    }

    try:
        result = subprocess.run(  # noqa: S603 - command path is resolved locally and arguments are fixed
            [node_executable, str(script_path)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=20,
        )

        if result.returncode == 0:
            return _result(True, None)

        error_message = result.stderr.strip() or result.stdout.strip()
        if result.stdout:
            with suppress(Exception):
                parsed = json.loads(result.stdout)
                error_message = parsed.get("error") or error_message

        logging.error("SMTP notification error (Nodemailer): %s", error_message)
        return _result(False, error_message)
    except (OSError, subprocess.SubprocessError) as exc:
        logging.error("SMTP notification subprocess error: %s", exc)
        return _result(False, str(exc))


def notify(
    title: str,
    message: str,
    tags: str,
    event_type: str = "user_joined",
    previous_version: str | None = None,
    new_version: str | None = None,
):
    """Broadcast to every configured agent that is subscribed to the event type."""
    for agent in Notification.query.all():
        # Check if agent is subscribed to this event type
        subscribed_events = (
            agent.notification_events.split(",") if agent.notification_events else []
        )
        if event_type not in subscribed_events:
            continue

        if agent.type == "discord":
            _discord(message, agent.url, title, previous_version, new_version)
        elif agent.type == "ntfy":
            _ntfy(message, title, tags, agent.url, agent.username, agent.password)
        elif agent.type == "apprise":
            _apprise(message, title, tags, agent.url)
        elif agent.type == "notifiarr":
            _notifiarr(message, title, agent.url, agent.channel_id)
        elif agent.type == "smtp":
            _smtp(
                message,
                title,
                agent.url,
                agent.smtp_port,
                agent.username,
                agent.password,
                agent.smtp_from_email,
                agent.smtp_to_emails,
                agent.smtp_encryption,
            )
