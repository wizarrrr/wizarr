import app.notifications.providers as notification_providers

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
