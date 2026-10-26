"""Approval-gated access requests; passwords stay in the existing invite flow."""

import hashlib
import hmac
import secrets
import smtplib
import ssl
import string
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from urllib.parse import urlsplit

from flask import current_app
from sqlalchemy import update

from app.extensions import db
from app.models import Invitation, MediaServer, Settings, SignupRequest


def signup_enabled():
    setting = Settings.query.filter_by(key="public_signup_enabled").first()
    return bool(setting and setting.value == "true")


def submit_request(name, email, message, remote_address):
    """Return a new request or None for a duplicate, without exposing which."""
    email = email.strip().casefold()
    if SignupRequest.query.filter_by(email=email).first():
        return None
    now = datetime.now(UTC)
    secret = str(current_app.config["SECRET_KEY"]).encode()
    source = hmac.new(secret, remote_address.encode(), hashlib.sha256).hexdigest()
    recent = SignupRequest.query.filter(
        SignupRequest.source_hash == source,
        SignupRequest.created_at >= now - timedelta(hours=1),
    ).count()
    if recent >= 5:
        raise ValueError("rate_limit")
    if SignupRequest.query.filter_by(status="pending").count() >= 500:
        raise ValueError("queue_full")
    item = SignupRequest(
        name=name.strip(), email=email, message=message.strip(), source_hash=source
    )
    db.session.add(item)
    db.session.commit()
    return item


def approve_request(item_id, server_id, reviewer):
    """Claim a pending request and create exactly one invite in one transaction."""
    server = db.session.get(MediaServer, server_id)
    if not server or not server.verified:
        raise ValueError("Select a verified media server.")
    changed = db.session.execute(
        update(SignupRequest)
        .where(SignupRequest.id == item_id, SignupRequest.status == "pending")
        .values(status="approved", reviewed_at=datetime.now(UTC), reviewed_by=reviewer)
    )
    if changed.rowcount != 1:
        db.session.rollback()
        raise ValueError("This request has already been reviewed.")
    item = db.session.get(SignupRequest, item_id)
    invite = Invitation(
        code="".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10)
        ),
        expires=datetime.now(UTC) + timedelta(days=7),
        unlimited=False,
        allow_downloads=server.allow_downloads,
        allow_live_tv=server.allow_live_tv,
        allow_mobile_uploads=server.allow_mobile_uploads,
    )
    invite.servers.append(server)
    db.session.add(invite)
    db.session.flush()
    item.invitation_id = invite.id
    db.session.commit()
    return item


def reject_request(item_id, reviewer):
    result = db.session.execute(
        update(SignupRequest)
        .where(SignupRequest.id == item_id, SignupRequest.status == "pending")
        .values(status="rejected", reviewed_at=datetime.now(UTC), reviewed_by=reviewer)
    )
    db.session.commit()
    return result.rowcount == 1


def _public_url(path):
    base = current_app.config.get("SIGNUP_PUBLIC_URL", "").rstrip("/")
    parsed = urlsplit(base)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Set SIGNUP_PUBLIC_URL to the public Wizarr URL.")
    return base + path


def _send_email(recipient, subject, body):
    config = current_app.config
    host = config.get("SIGNUP_SMTP_HOST")
    sender = config.get("SIGNUP_SMTP_FROM")
    if not host or not sender or not recipient:
        raise ValueError("Signup email is not configured.")
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    port = config.get("SIGNUP_SMTP_PORT", 587)
    connection = smtplib.SMTP_SSL if config.get("SIGNUP_SMTP_SSL") else smtplib.SMTP
    with connection(host, port, timeout=15) as smtp:
        if not config.get("SIGNUP_SMTP_SSL"):
            smtp.starttls(context=ssl.create_default_context())
        if config.get("SIGNUP_SMTP_USERNAME"):
            smtp.login(
                config["SIGNUP_SMTP_USERNAME"], config.get("SIGNUP_SMTP_PASSWORD", "")
            )
        smtp.send_message(message)


def notify_owner(item):
    _send_email(
        current_app.config.get("SIGNUP_ADMIN_EMAIL"),
        "Wizarr: new access request",
        f"{item.name} ({item.email}) requested access.\n\n"
        f"{item.message}\n\nReview: {_public_url('/admin/signups')}\n"
        "No media account has been created.",
    )


def send_approval(item):
    invite = item.invitation
    if item.status != "approved" or not invite or invite.used:
        raise ValueError("No unused approved invitation is available.")
    if invite.expires and invite.expires.replace(tzinfo=UTC) <= datetime.now(UTC):
        raise ValueError(
            "This invitation has expired. Create a new invitation instead."
        )
    _send_email(
        item.email,
        "Your media access request was approved",
        f"Hi {item.name},\n\nYour request was approved. Choose your username and password here:\n"
        f"{_public_url('/j/' + invite.code)}\n\n"
        f"This personal, single-use link expires on {invite.expires:%Y-%m-%d %H:%M} UTC. Please do not share it.\n"
        "After setup, follow the onboarding guide to connect your apps and request media.",
    )
    item.email_sent_at = datetime.now(UTC)
    db.session.commit()
