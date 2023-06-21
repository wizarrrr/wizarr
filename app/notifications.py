import logging
import requests
import json
import base64

from app import app, Settings, Notifications


def notify(title, message, tags):
    for agents in Notifications.select():
        if agents.type == "discord":
            notify_discord(message, agents.url)
        elif agents.type == "ntfy":
            notify_ntfy(message, title, tags, agents.url, agents.username, agents.password)
        elif agents.type == "telegram":
            notify_telegram(message, agents.url, agents.username)
        elif agents.type == "pushover":
            notify_pushover(message, title, agents.url, agents.username, agents.password)


def notify_discord(message, webhook_url):
    data = json.dumps({"content": message})
    headers = {"Content-Type": "application/json"}
    success = send_request(webhook_url, data, headers)
    if not success:
        logging.error(f"Failed to send Discord message. URL is invalid: {webhook_url}")
    return success

def notify_telegram(message, bot_token, chat_id):
    data = json.dumps({"chat_id": chat_id, "text": message})
    headers = {"Content-Type": "application/json"}
    success = send_request(f"https://api.telegram.org/bot{bot_token}/sendMessage", data, headers)
    if not success:
        logging.error(f"Failed to send Telegram message. Invalid bot token or chat ID")
    return success

def notify_ntfy(message, title, tags, url, username, password):
    headers = {"Title": title,
               "Tags": tags}

    if username and password:
        credentials = f"{username}:{password}"
        base64_credentials = base64.b64encode(credentials.encode()).decode()
        headers["Authorization"] = f"Basic {base64_credentials}"

    success = send_request(url, message, headers)
    if not success:
        logging.error(f"Failed to send ntfy message. Invalid URL")
    return success

def notify_pushover(message, title, url, username, password):
    data = json.dumps({"token": password, "user": username, "message": message, "title": title})
    headers = {"Content-Type": "application/json"}
    
    success = send_request(url, data, headers)
    if not success:
        logging.error(f"Failed to send Pushover message. Invalid URL or Token")
    return success
    
            

def send_request(url, data, headers):
    try:
        response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200 or response.status_code == 204:
            return True
        else:
            logging.error(f"Failed to send message. Error code: {response.status_code}, Error message: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed due to an error: {e}")
        return False
