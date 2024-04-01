from requests import post
from schematics.types import StringType

from app.notifications.exceptions import NotificationSendError, NotificationStatusError
from app.notifications.model import Model


class PushoverResource(Model):
    name = StringType(default="Pushover", metadata={"name": "Pushover", "icon": "bell", "description": 'e.g. "Pushover"'})
    base_url = StringType(default="https://api.pushover.net/1/", metadata={"name": "Base URL", "description": 'e.g. "https://api.pushover.net/1/"'})
    token = StringType(required=True, metadata={"name": "API Token", "description": 'e.g. "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5"'})
    user = StringType(required=True, metadata={"name": "User Key", "description": 'e.g. "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5"'})
    device = StringType(required=False, default=None, metadata={"name": "Device Name", "description": 'e.g. "iPhone"'})

    template = {
        "name": "Pushover",
        "logo": "https://pushover.net/images/pushover-logo.svg",
        "description": "Pushover is a simple push notification service to instantly send alerts to Android and iOS devices."
    }


class Pushover(PushoverResource):
    """
    A pushover notification

    :param token: The pushover API token
    :param user: The pushover user key
    :param device: The pushover device name

    :raises ResourceError: If the pushover API returns an error
    """

    def send(self, **kwargs):
        """
        Send a pushover notification

        :param title: The title of the notification
        :param message: The message of the notification

        :return: The response from the pushover API
        """

        payload = {
            "token": self.token,
            "user": self.user,
            "message": kwargs.get("message"),
        }

        if kwargs.get("title"):
            payload.update({"title": kwargs.get("title")})

        if self.device:
            payload.update({"device": self.device})

        try:
            response = post(f"{self.base_url}messages.json", data=payload, timeout=10)
        except Exception as e:
            raise NotificationSendError(f"Pushover error: {e}") from e

        if response.status_code != 200:
            raise NotificationStatusError(f"Pushover error: {response.text}")

        return response.json()
