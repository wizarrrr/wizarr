import base64
import json
import logging

import apprise
import requests

from app.models import Notification

__all__ = ["notify"]


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


def _discord(msg: str, webhook_url: str) -> bool:
    data = json.dumps({"content": msg})
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


def _apprise(msg: str, title: str, tags: str, url: str) -> bool:
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


def notify(title: str, message: str, tags: str):
    """Broadcast to every configured agent."""
    for agent in Notification.query.all():
        if agent.type == "discord":
            _discord(message, agent.url)
        elif agent.type == "ntfy":
            _ntfy(message, title, tags, agent.url, agent.username, agent.password)
        elif agent.type == "apprise":
            _apprise(message, title, tags, agent.url)
        elif agent.type == "notifiarr":
            _notifiarr(message, title, agent.url, agent.channel_id)
