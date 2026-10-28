import logging
import smtplib
import ssl
from email.message import EmailMessage

from flask import render_template

from app.models import SMTPConfiguration, User
from app.services.ldap.encryption import decrypt_credential

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Raised when an email could not be sent. Callers decide whether to swallow it."""


def _get_active_config() -> SMTPConfiguration | None:
    config = SMTPConfiguration.query.first()
    if not config or not config.enabled:
        return None
    return config


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    config: SMTPConfiguration | None = None,
) -> None:
    """Low-level send. Raises EmailSendError on any failure."""
    config = config or _get_active_config()
    if config is None:
        raise EmailSendError("SMTP is not configured or not enabled")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = (
        f"{config.from_name} <{config.from_email}>"
        if config.from_name
        else config.from_email
    )
    msg["To"] = to_email
    msg.set_content(text_body or html_body)
    if text_body:
        msg.add_alternative(html_body, subtype="html")

    password = (
        decrypt_credential(config.password_encrypted)
        if config.password_encrypted
        else None
    )

    try:
        if config.encryption == "ssl":
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                config.host, config.port, context=context, timeout=10
            ) as server:
                if config.username and password:
                    server.login(config.username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(config.host, config.port, timeout=10) as server:
                if config.encryption == "starttls":
                    server.starttls(context=ssl.create_default_context())
                if config.username and password:
                    server.login(config.username, password)
                server.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("Failed to send email to %s: %s", to_email, exc)
        raise EmailSendError(str(exc)) from exc


def send_invite_email(to_email: str, invite_link: str, invite_code: str) -> None:
    html = render_template("email/invite.html", link=invite_link, code=invite_code)
    text = render_template("email/invite.txt", link=invite_link, code=invite_code)
    send_email(to_email, "You've been invited", html, text)


def send_expiry_reminder_email(user: User, days_left: int) -> None:
    html = render_template("email/expiry_reminder.html", user=user, days_left=days_left)
    text = render_template("email/expiry_reminder.txt", user=user, days_left=days_left)
    send_email(user.email, "Your access is expiring soon", html, text)


def send_test_email(to_email: str, config: SMTPConfiguration) -> None:
    """Used by the settings 'send test email' button, with an unsaved config."""
    send_email(
        to_email,
        "Wizarr SMTP test email",
        "<p>This is a test email from Wizarr. If you received this, SMTP is configured correctly.</p>",
        "This is a test email from Wizarr. If you received this, SMTP is configured correctly.",
        config=config,
    )
