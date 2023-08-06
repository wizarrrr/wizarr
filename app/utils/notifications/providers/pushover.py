from notifications.exceptions import NotificationSendError, NotificationStatusError

from requests import post
from typing import Optional

class PushoverMixin:
    name = "pushover"
    base_url = "https://api.pushover.net/1/"


class PushoverResource:
    """
    A pushover resource to store authentication details

    :param token: The pushover API token
    :param user: The pushover user key
    :param device: The pushover device name
    """

    token: str
    user: str
    device: str

    def __init__(self, token: str, user: str, device: Optional[str] = None):
        self.token = token
        self.user = user
        self.device = device

    def to_primitive(self):
        return {
            "token": self.token,
            "user": self.user,
            "device": self.device,
        }


class Pushover(PushoverResource, PushoverMixin):
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
