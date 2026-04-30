import base64
import hashlib
import hmac
import ipaddress
import json
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import apprise
import requests

from app.models import Notification

__all__ = ["notify", "is_webhook_url_allowed"]


def is_webhook_url_allowed(url: str) -> bool:
    """Return True iff url uses https, or uses http with a loopback host.

    Webhook agents can carry sensitive payloads (plaintext passwords when the
    agent opts in), so we refuse plaintext http over the network. Loopback is
    permitted for local docker / host-side integrations.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme == "https":
        return True
    if parsed.scheme != "http":
        return False
    host = (parsed.hostname or "").lower()
    if host in ("localhost", "host.docker.internal"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


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
    embed: dict[str, Any] = {
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


def _telegram(
    msg: str,
    title: str,
    baseUrl: str,
    bot_token: str,
    chat_id: str,
) -> bool:
    baseUrl = baseUrl.rstrip("/")
    url = f"{baseUrl}/bot{bot_token}/sendMessage"
    data = json.dumps(
        {
            "chat_id": chat_id,
            "text": f"{title}\n{msg}",
        }
    )
    headers = {"Content-Type": "application/json"}
    return _send(url, data, headers)


def _webhook(
    url: str,
    secret: str | None,
    event_type: str,
    title: str,
    message: str,
    context: dict[str, Any] | None,
    include_password: bool,
) -> bool:
    """POST a structured JSON payload to an external webhook.

    Payload schema is versioned via the "event" field so new events can be
    added without breaking existing consumers. If include_password is False,
    the "password" field is stripped before sending regardless of what the
    caller supplied in context.
    """
    if not is_webhook_url_allowed(url):
        logging.error(
            "Webhook URL rejected (must be https or loopback http): %s", url
        )
        return False

    safe_context = dict(context or {})
    if not include_password:
        safe_context.pop("password", None)

    payload = {
        "event": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "title": title,
        "message": message,
        **safe_context,
    }
    body = json.dumps(payload, separators=(",", ":")).encode()

    headers = {"Content-Type": "application/json"}
    if secret:
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Wizarr-Signature"] = f"sha256={sig}"

    return _send(url, body, headers)


def notify(
    title: str,
    message: str,
    tags: str,
    event_type: str = "user_joined",
    previous_version: str | None = None,
    new_version: str | None = None,
    context: dict[str, Any] | None = None,
):
    """Broadcast to every configured agent that is subscribed to the event type.

    `context` carries structured data for webhook-style agents. It is ignored
    by human-facing agents (Discord, ntfy, etc.) that only render a title and
    message. When an agent is type="webhook", context is merged into the JSON
    payload; if the agent has include_password=False, the plaintext password
    is stripped before sending.
    """
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
        elif agent.type == "telegram":
            _telegram(
                message,
                title,
                agent.url,
                agent.telegram_bot_token,
                agent.telegram_chat_id,
            )
        elif agent.type == "webhook":
            _webhook(
                agent.url,
                agent.webhook_secret,
                event_type,
                title,
                message,
                context,
                bool(agent.include_password),
            )
