import logging
import requests
import json

from app import app, Settings, Notifications


def notify(kind, identifier):
    if kind == "plex_new":
        for agent in Notifications.select():
            if agent.type == "discord":
                notify_discord(f"User {identifier} has been invited to your Plex Server!", agent.url)
            elif agent.type == "ntfy":
                notify_ntfy(f"User {identifier} has been invited to your Plex Server!", "New User", "tada", agent.url,
                            agent.username, agent.password)
        return
    if kind == "jellyfin_new":
        for agent in Notifications.select():
            if agent.type == "discord":
                notify_discord(f"User {identifier} has been invited to your Jellyfin Server!", agent.url)
            elif agent.type == "ntfy":
                notify_ntfy(f"User {identifier} has been invited to your Jellyfin Server!", "New User", "tada",
                            agent.url,
                            agent.username, agent.password)


def notify_discord(message, webhook_url):
    try:
        response = requests.post(webhook_url, data=json.dumps({"content": message}),
                                 headers={"Content-Type": "application/json"})
    except:
        logging.error(f"Failed to send message. URL is invalid: {webhook_url}")
        return False
    if response.status_code == 204 or response.status_code == 200:
        pass
        return True
    else:
        logging.error(f"Failed to send message. Error code: {response.status_code}, Error message: {response.text}")
        return False


def notify_ntfy(message, title, tags, url, username, password):
    try:
        response = requests.post(url,
                                 data=message,
                                 headers={
                                     "Title": title,
                                     "Tags": tags
                                     # "Authorization":
                                 })
    except:
        logging.error(f"Failed to send message. Invalid URL")
        return False
    if response.status_code == 200 or response.status_code == 204:
        pass
        return True
    else:
        logging.error(f"Failed to send message. Error code: {response.status_code}, Error message: {response.text}")
        return False
