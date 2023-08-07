from ..exceptions import NotificationSendError, NotificationStatusError
from smtplib import SMTP as SMTPClient
from ssl import create_default_context

class SMTPMixin:
    name = "smtp"
    base_url = "smtp://"

class SMTPResource:
    """
    A smtp resource to store authentication details

    :param smtp_server: The smtp server url
    :param port: The smtp server port
    :param username: The smtp server username
    :param password: The smtp server password
    :param receiver: The smtp server receiver
    :param starttls: The smtp server starttls
    """

    smtp_server: str
    port: int
    username: str
    password: str
    receiver: str
    starttls: bool

    def __init__(self, smtp_server: str, port: int, username: str, password: str, receiver: str, starttls: bool = True):
        self.smtp_server = smtp_server
        self.port = port
        self.username = username
        self.password = password
        self.receiver = receiver
        self.starttls = starttls

    def to_primitive(self):
        return {
            "smtp_server": self.smtp_server,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "receiver": self.receiver,
            "starttls": self.starttls,
        }


class SMTP(SMTPResource, SMTPMixin):
    """
    A smtp notification

    :param smtp_server: The smtp server url
    :param port: The smtp server port
    :param username: The smtp server username
    :param password: The smtp server password

    :raises ResourceError: If the smtp API returns an error
    """

    def send(self, **kwargs):
        """
        Send a smtp notification

        :param title: The title of the notification
        :param message: The message of the notification

        :return: The response from the smtp API
        """

        message = f"Subject: {kwargs.get('title')}\n\n{kwargs.get('message')}"

        # Send the notification
        try:
            client = SMTPClient(self.smtp_server, self.port)

            if self.starttls:
                context = create_default_context()
                client.starttls(context=context)

            client.login(self.username, self.password)
            client.sendmail(self.username, self.receiver, message)
            client.quit()
        except Exception as e:
            raise NotificationSendError(str(e)) from e

        # Return the response
        return True
