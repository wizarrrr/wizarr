from __future__ import annotations

from datetime import datetime
from html import escape

from app.models import Notification
from app.services.notifications import _smtp


def _format_expiry(expires: datetime | None) -> str:
    if not expires:
        return "no expiry date set"

    if expires.tzinfo:
        return expires.strftime("%Y-%m-%d %H:%M %Z")
    return expires.strftime("%Y-%m-%d %H:%M UTC")


def _wrap_html_email(
    title: str,
    intro: str,
    details: list[tuple[str, str]],
    footer: str,
) -> str:
    detail_rows = "".join(
        (
            '<tr><td style="padding:8px 0;color:#6b7280;font-size:13px;">'
            f"{escape(label)}</td><td style=\"padding:8px 0;color:#111827;font-size:13px;font-weight:600;\">"
            f"{escape(value)}</td></tr>"
        )
        for label, value in details
    )

    return (
        '<div style="background:#f3f4f6;padding:24px;font-family:Inter,Segoe UI,Arial,sans-serif;">'
        '<div style="max-width:640px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,0.08);">'
        '<div style="background:linear-gradient(120deg,#0ea5e9,#0284c7);padding:20px 24px;">'
        '<div style="color:#ffffff;font-size:18px;font-weight:700;">Wizarr</div>'
        '</div>'
        '<div style="padding:24px;">'
        f'<h2 style="margin:0 0 12px 0;color:#111827;font-size:20px;">{escape(title)}</h2>'
        f'<p style="margin:0 0 16px 0;color:#374151;font-size:14px;line-height:1.6;">{escape(intro)}</p>'
        '<table style="width:100%;border-collapse:collapse;margin:8px 0 18px 0;">'
        f"{detail_rows}"
        '</table>'
        f'<p style="margin:0;color:#4b5563;font-size:13px;line-height:1.6;">{escape(footer)}</p>'
        '</div></div></div>'
    )


def _get_subject_and_message(
    event_type: str,
    username: str,
    expires: datetime | None,
    reason: str | None = None,
) -> tuple[str, str, str]:
    expiry_text = _format_expiry(expires)

    if event_type == "user_created_confirmation":
        subject = "Your Wizarr account is active"
        text = (
            f"Hello {username},\n\n"
            "Your account has been created successfully.\n"
            f"It is active until {expiry_text}.\n\n"
            "If you need help, please contact your server administrator."
        )
        html = _wrap_html_email(
            subject,
            "Your account has been created successfully.",
            [
                ("User", username),
                ("Status", "Active"),
                ("Active Until", expiry_text),
            ],
            "If you need help, please contact your server administrator.",
        )
        return subject, text, html

    if event_type == "user_expired_notification":
        subject = "Your Wizarr account has expired"
        text = (
            f"Hello {username},\n\n"
            "Your account has expired and access has been removed.\n"
            f"Expiry date: {expiry_text}.\n\n"
            "If you need access again, please contact your server administrator."
        )
        html = _wrap_html_email(
            subject,
            "Your account has expired and access has been removed.",
            [
                ("User", username),
                ("Status", "Expired"),
                ("Expiry Date", expiry_text),
            ],
            "If you need access again, please contact your server administrator.",
        )
        return subject, text, html

    action_label = (
        "Disabled"
        if event_type == "user_manually_disabled_notification"
        else "Deleted"
    )
    reason_text = reason.strip() if reason else "No reason provided"
    subject = f"Your Wizarr account was {action_label.lower()}"
    text = (
        f"Hello {username},\n\n"
        f"Your account was manually {action_label.lower()} by an administrator.\n"
        f"Reason: {reason_text}.\n\n"
        "If you think this was a mistake, please contact your server administrator."
    )
    html = _wrap_html_email(
        subject,
        f"Your account was manually {action_label.lower()} by an administrator.",
        [
            ("User", username),
            ("Action", action_label),
            ("Reason", reason_text),
        ],
        "If you think this was a mistake, please contact your server administrator.",
    )
    return subject, text, html


def send_user_lifecycle_email(
    event_type: str,
    recipient_email: str | None,
    username: str,
    expires: datetime | None,
    reason: str | None = None,
) -> bool:
    if event_type not in {
        "user_created_confirmation",
        "user_expired_notification",
        "user_manually_deleted_notification",
        "user_manually_disabled_notification",
    }:
        return False
    if not recipient_email:
        return False

    subject, message, html_message = _get_subject_and_message(
        event_type,
        username,
        expires,
        reason,
    )

    sent = False
    for agent in Notification.query.filter_by(type="smtp").all():
        subscribed_events = (
            agent.notification_events.split(",") if agent.notification_events else []
        )
        if event_type not in subscribed_events:
            continue

        ok = _smtp(
            message,
            subject,
            agent.url,
            agent.smtp_port,
            agent.username,
            agent.password,
            agent.smtp_from_email,
            recipient_email,
            agent.smtp_encryption,
            html_message=html_message,
        )
        sent = sent or bool(ok)

    return sent
