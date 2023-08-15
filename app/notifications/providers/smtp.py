from smtplib import SMTP as SMTPClient
from ssl import create_default_context

from schematics.models import Model
from schematics.types import StringType, IntType, BooleanType

from app.notifications.exceptions import NotificationSendError


class SMTPResource(Model):
    name = StringType(default="SMTP", metadata={"name": "SMTP", "hidden": True, "icon": "envelope", "description": 'e.g. "SMTP"'})
    smtp_server = StringType(required=True, metadata={"name": "SMTP Server", "type": "url", "description": 'e.g. "smtp.wizarr.dev"'})
    port = IntType(required=True, default=25, metadata={"name": "Port", "description": 'e.g. "25"'})
    username = StringType(required=True, metadata={"name": "Username", "description": 'e.g. "wizarr@wizarr.dev'})
    password = StringType(required=True, metadata={"name": "Password", "type": "password", "description": 'e.g. "password"'})
    receiver = StringType(required=True, metadata={"name": "Receiver", "type": "email", "description": 'e.g. "admin@wizarr.dev'})
    starttls = BooleanType(required=False, default=False, metadata={"name": "StartTLS", "type": "checkbox", "description": 'e.g. "False"'})


class SMTP(SMTPResource):
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
