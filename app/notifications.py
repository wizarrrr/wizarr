import logging
import requests
import json

from app import app, Settings


def notify():
    if Settings.get("notification_discord"):
        pass
    if Settings.get("notification_ntfy"):
        pass


def notify_discord(message):
    webhook_url = Settings.get("notification_discord_webhook")
    response = requests.post(webhook_url, data=json.dumps({"content": message}),
                             headers={"Content-Type": "application/json"})
    if response.status_code == 204:
        pass
    else:
        logging.error(f"Failed to send message. Error code: {response.status_code}, Error message: {response.text}")


def notify_ntfy(message, title, tags):
    requests.post("https://ntfy.sh/matthieu_oratoire_jaseroque",
                  data=message,
                  headers={
                      "Title": title,
                      "Tags": tags
                      #"Authorization":
                  })


notify_ntfy("This is a test", "Hello", "tada")
