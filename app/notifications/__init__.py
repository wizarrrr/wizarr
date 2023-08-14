import base64
import json
import logging

import requests

import app.notifications.providers as notification_providers
from app.models.database.notifications import Notifications

from .exceptions import InvalidNotificationAgent

# Take an array of class and send a notification to each one
def send_notifications(providers: [notification_providers], **kwargs):
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
def send_notification(provider: notification_providers, **kwargs):
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
    # pylint: disable=consider-using-dict-items
    for provider in notification_providers.__resources__:
        # Get the resource to convert to a schema
        resource = notification_providers.__resources__[provider]["resource"]
        notification = notification_providers.__resources__[provider]["notification"]
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

print(get_providers_schema())