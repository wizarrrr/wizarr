"""Unit tests for the SMTP email-sending service."""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app.models import SMTPConfiguration
from app.services.email import EmailSendError, send_email
from app.services.ldap.encryption import encrypt_credential


@pytest.fixture
def smtp_config(session):
    config = SMTPConfiguration(
        enabled=True,
        host="smtp.example.com",
        port=587,
        encryption="starttls",
        username="user@example.com",
        password_encrypted=encrypt_credential("secret"),
        from_email="wizarr@example.com",
        from_name="Wizarr",
        reminder_days_before=3,
    )
    session.add(config)
    session.commit()
    yield config
    SMTPConfiguration.query.delete()
    session.commit()


def test_send_email_raises_when_not_configured(session):
    assert SMTPConfiguration.query.first() is None

    with pytest.raises(EmailSendError):
        send_email("to@example.com", "Subject", "<p>Hi</p>")


def test_send_email_raises_when_disabled(session):
    config = SMTPConfiguration(
        enabled=False,
        host="smtp.example.com",
        port=587,
        encryption="none",
        from_email="wizarr@example.com",
        reminder_days_before=3,
    )
    session.add(config)
    session.commit()

    try:
        with pytest.raises(EmailSendError):
            send_email("to@example.com", "Subject", "<p>Hi</p>")
    finally:
        SMTPConfiguration.query.delete()
        session.commit()


def test_send_email_uses_starttls_and_logs_in(smtp_config):
    with patch("app.services.email.smtplib.SMTP") as smtp_cls:
        server = MagicMock()
        smtp_cls.return_value.__enter__.return_value = server

        send_email("to@example.com", "Subject", "<p>Hi</p>", "Hi")

    server.starttls.assert_called_once()
    server.login.assert_called_once_with("user@example.com", "secret")
    server.send_message.assert_called_once()
    sent_msg = server.send_message.call_args[0][0]
    assert sent_msg["To"] == "to@example.com"
    assert sent_msg["Subject"] == "Subject"
    assert "Wizarr" in sent_msg["From"]


def test_send_email_uses_ssl(smtp_config):
    smtp_config.encryption = "ssl"

    with patch("app.services.email.smtplib.SMTP_SSL") as smtp_ssl_cls:
        server = MagicMock()
        smtp_ssl_cls.return_value.__enter__.return_value = server

        send_email("to@example.com", "Subject", "<p>Hi</p>")

    server.login.assert_called_once()
    server.send_message.assert_called_once()


def test_send_email_wraps_smtp_exceptions(smtp_config):
    with patch("app.services.email.smtplib.SMTP") as smtp_cls:
        server = MagicMock()
        server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad creds")
        smtp_cls.return_value.__enter__.return_value = server

        with pytest.raises(EmailSendError):
            send_email("to@example.com", "Subject", "<p>Hi</p>")
