from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from flask import current_app, render_template
from flask_babel import force_locale, format_datetime
from flask_babel import gettext as _
from flask_mail import Mail, Message

from app.config import load_secrets, save_secrets
from app.extensions import db
from app.models import Settings, User

SMTP_PASSWORD_KEY_NAME = "smtp_password"  # noqa: S105
SMTP_BOOLEAN_KEYS = {"smtp_enabled", "smtp_use_tls", "smtp_use_ssl"}
SMTP_SETTING_DEFAULTS: dict[str, Any] = {
    "smtp_enabled": False,
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_from_address": "",
    "smtp_from_name": "Wizarr",
    "smtp_use_tls": True,
    "smtp_use_ssl": False,
    "smtp_language": "en",
}
SMTP_SETTING_KEYS = tuple(SMTP_SETTING_DEFAULTS)


def _coerce_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _coerce_port(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 587


def get_smtp_settings(*, include_password: bool = True) -> dict[str, Any]:
    settings = SMTP_SETTING_DEFAULTS.copy()
    rows = Settings.query.filter(Settings.key.in_(SMTP_SETTING_KEYS)).all()
    for row in rows:
        if row.key in SMTP_BOOLEAN_KEYS:
            settings[row.key] = _coerce_bool(row.value)
        elif row.key == "smtp_port":
            settings[row.key] = _coerce_port(row.value)
        elif row.key == "smtp_language":
            settings[row.key] = row.value if row.value in {"en", "de"} else "en"
        else:
            settings[row.key] = row.value or SMTP_SETTING_DEFAULTS.get(row.key, "")

    if include_password:
        settings["smtp_password"] = load_secrets().get(SMTP_PASSWORD_KEY_NAME, "")

    return settings


def save_smtp_settings(data: dict[str, Any]) -> None:
    password = data.pop("smtp_password", None)

    try:
        for key, value in data.items():
            if key not in SMTP_SETTING_KEYS:
                continue

            if key in SMTP_BOOLEAN_KEYS:
                value = "true" if bool(value) else "false"
            elif key == "smtp_port":
                value = str(_coerce_port(value))
            elif value is None:
                value = ""
            else:
                value = str(value)

            setting = Settings.query.filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                db.session.add(Settings(key=key, value=value))

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    if password is not None:
        secrets = load_secrets()
        if password:
            secrets[SMTP_PASSWORD_KEY_NAME] = password
        else:
            secrets.pop(SMTP_PASSWORD_KEY_NAME, None)
        save_secrets(secrets)


def _mail_enabled(settings: dict[str, Any]) -> bool:
    return bool(
        settings.get("smtp_enabled")
        and settings.get("smtp_host")
        and settings.get("smtp_from_address")
    )


def _apply_mail_config(settings: dict[str, Any]) -> Mail:
    app = current_app._get_current_object()
    app.config.update(
        MAIL_SERVER=settings["smtp_host"],
        MAIL_PORT=settings["smtp_port"],
        MAIL_USERNAME=settings.get("smtp_username") or None,
        MAIL_PASSWORD=settings.get("smtp_password") or None,
        MAIL_USE_TLS=bool(settings.get("smtp_use_tls")),
        MAIL_USE_SSL=bool(settings.get("smtp_use_ssl")),
        MAIL_DEFAULT_SENDER=(
            settings.get("smtp_from_name") or "Wizarr",
            settings["smtp_from_address"],
        ),
        MAIL_SUPPRESS_SEND=app.config.get("TESTING", False),
    )
    return Mail(app)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _event_content(event_type: str, server_name: str) -> dict[str, str]:
    if event_type == "activated":
        return {
            "badge": _("Account Active"),
            "headline": _("Your account is now active"),
            "summary": _("Your access to {server} has been activated.").format(
                server=server_name
            ),
        }
    if event_type == "expired":
        return {
            "badge": _("Account Expired"),
            "headline": _("Your account has expired"),
            "summary": _("Your access to {server} has expired.").format(
                server=server_name
            ),
        }
    return {
        "badge": _("Account Deleted"),
        "headline": _("Your account has been deleted"),
        "summary": _("Your access to {server} has been removed.").format(
            server=server_name
        ),
    }


def send_user_lifecycle_email(
    user: User,
    *,
    event_type: str,
    server_name: str | None = None,
    expires_at: datetime | None = None,
    action_label: str | None = None,
) -> bool:
    if not user.email:
        return False

    settings = get_smtp_settings(include_password=True)
    if not _mail_enabled(settings):
        return False

    locale = settings.get("smtp_language", "en")
    resolved_server_name = server_name or (
        user.server.name
        if user.server
        else (current_app.config.get("SERVER_NAME") or "Wizarr")
    )
    expires_at = _normalize_datetime(expires_at or user.expires)

    try:
        with force_locale(locale):
            if event_type == "expired" and not action_label:
                action_label = _("deleted")
            elif action_label == "disabled":
                action_label = _("disabled")
            elif action_label == "deleted":
                action_label = _("deleted")
            content = _event_content(event_type, resolved_server_name)
            expiry_label = (
                format_datetime(expires_at, format="medium") if expires_at else None
            )
            html_body = render_template(
                "email/user_lifecycle.html",
                user=user,
                server_name=resolved_server_name,
                event_type=event_type,
                action_label=action_label,
                expires_label=expiry_label,
                locale=locale,
                sent_at=format_datetime(datetime.now(UTC), format="medium"),
                content=content,
            )
            text_body = render_template(
                "email/user_lifecycle.txt",
                user=user,
                server_name=resolved_server_name,
                event_type=event_type,
                action_label=action_label,
                expires_label=expiry_label,
                content=content,
            )
            subject = _("{headline} · {server}").format(
                headline=content["headline"], server=resolved_server_name
            )

        mail = _apply_mail_config(settings)
        message = Message(
            subject=subject,
            recipients=[user.email],
            body=text_body,
            html=html_body,
        )
        mail.send(message)
    except Exception as exc:
        logging.warning("Failed to send lifecycle email for user %s: %s", user.id, exc)
        return False

    logging.info("Lifecycle email '%s' sent to %s", event_type, user.email)
    return True
