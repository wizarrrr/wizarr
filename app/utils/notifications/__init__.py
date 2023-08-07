import base64
import json
import logging

import requests

import app.utils.notifications.providers as providers
from app.models.database.notifications import Notifications

from .exceptions import InvalidNotificationAgent


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
        logging.error("Failed to send Discord message. URL is invalid: %s", webhook_url)
        raise InvalidNotificationAgent("Failed to send Discord message. URL is invalid")
    return success

def notify_telegram(message, bot_token, chat_id):
    data = json.dumps({"chat_id": chat_id, "text": message})
    headers = {"Content-Type": "application/json"}
    success = send_request(f"https://api.telegram.org/bot{bot_token}/sendMessage", data, headers)
    if not success:
        logging.error("Failed to send Telegram message. Invalid bot token or chat ID")
        raise InvalidNotificationAgent("Failed to send Telegram message. Invalid bot token or chat ID")

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
        logging.error("Failed to send ntfy message. Invalid URL")
        raise InvalidNotificationAgent("Failed to send ntfy message. Invalid URL")

    return success

def notify_pushover(message, title, url, username, password):
    data = json.dumps({"token": password, "user": username, "msg": message, "title": title})
    headers = {"Content-Type": "application/json"}

    success = send_request(url, data, headers)
    if not success:
        logging.error("Failed to send Pushover message. Invalid URL or Token")
        raise InvalidNotificationAgent("Failed to send Pushover message. Invalid URL or Token")

    return success



def send_request(url, data, headers):
    try:
        response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200 or response.status_code == 204:
            return True
        else:
            logging.error("Failed to send message. Error code: %s, Error message: %s", response.status_code, response.text)
            return False
    except requests.exceptions.RequestException as e:
        logging.error("Request failed due to an error: %s", e)
        return False


# Take an array of class and send a notification to each one
def send_notifications(providers: [providers], **kwargs):
    """
    Send a notification to a list of providers

    :param providers: A list of providers to send a notification to
    :param kwargs: The arguments to send to the provider

    :return: A dictionary of responses from the providers
    """

    # Response object
    response = {}

    # Loop through each provider and send a notification
    for provider in providers:
        response[provider.name] = provider.send(**kwargs)

    # Return the response
    return response

# Send a notification to a provider
def send_notification(provider: providers, **kwargs):
    """
    Send a notification to a provider

    :param provider: The provider to send a notification to
    :param kwargs: The arguments to send to the provider

    :return: The response from the provider
    """

    # Send the notification
    response = provider.send(**kwargs)

    # Return the response
    return response


# Get a schema for all the providers
def get_providers_schema():
    """
    Get a schema for all the providers

    :return: A dictionary of schemas for all the providers
    """

    # Response object
    response = []

    # Loop through each provider and get the schema
    for provider in providers.__resources__:
        # Get the resource to convert to a schema
        resource = providers.__resources__[provider]["resource"]
        notification = providers.__resources__[provider]["notification"]
        schema = []

        # Convert the resource class to a schema using the resources variable names
        for variable in resource.__annotations__:
            schema.append({
                "name": variable,
                "type": resource.__annotations__[variable].__name__,
                "display_name": variable.replace("_", " ").title()
            })

        # Add the schema to the response
        response.append({
            "name": provider,
            "type": resource.__name__,
            "notification": notification.__name__,
            "display_name": provider.replace("_", " ").title(),
            "variables": schema,
        })


    # Return the response
    return response
