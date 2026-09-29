"""Pakasir QRIS payment helpers for paid Wizarr invitations.

Pakasir does not currently sign webhook payloads with a dashboard-provided
secret. This integration therefore treats webhooks only as a notification and
uses layered controls before creating an invitation:

1. Require an unguessable receiver-side webhook token in the URL path.
2. Match webhook project, order_id, amount, and completed status to a pending
   local order.
3. Confirm the transaction with Pakasir's Transaction Detail API using the
   project API key that is never exposed to the browser.
4. Make completion idempotent so replayed webhooks return the existing invite.
"""

from __future__ import annotations

import datetime
import json
import os
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
from flask import current_app, url_for

from app.extensions import db
from app.models import Invitation, PakasirOrder, PakasirPlan
from app.services.invites import create_invite

DEFAULT_BASE_URL = "https://app.pakasir.com"


class PakasirConfigurationError(RuntimeError):
    """Raised when required Pakasir configuration is missing."""


class PakasirVerificationError(RuntimeError):
    """Raised when a Pakasir notification cannot be verified."""


@dataclass(frozen=True)
class PakasirConfig:
    enabled: bool
    project: str
    api_key: str
    webhook_token: str
    base_url: str = DEFAULT_BASE_URL


def get_pakasir_config() -> PakasirConfig:
    """Load Pakasir configuration from Flask config or environment variables."""
    cfg = current_app.config
    enabled_value = cfg.get(
        "PAKASIR_ENABLED", os.getenv("WIZARR_PAKASIR_ENABLED", "false")
    )
    enabled = str(enabled_value).lower() in {"true", "1", "yes", "on"}
    project = str(
        cfg.get("PAKASIR_PROJECT", os.getenv("WIZARR_PAKASIR_PROJECT", ""))
    ).strip()
    api_key = str(
        cfg.get("PAKASIR_API_KEY", os.getenv("WIZARR_PAKASIR_API_KEY", ""))
    ).strip()
    webhook_token = str(
        cfg.get("PAKASIR_WEBHOOK_TOKEN", os.getenv("WIZARR_PAKASIR_WEBHOOK_TOKEN", ""))
    ).strip()
    base_url = str(
        cfg.get(
            "PAKASIR_BASE_URL",
            os.getenv("WIZARR_PAKASIR_BASE_URL", DEFAULT_BASE_URL),
        )
    ).rstrip("/")
    return PakasirConfig(
        enabled=enabled,
        project=project,
        api_key=api_key,
        webhook_token=webhook_token,
        base_url=base_url,
    )


def ensure_pakasir_config(config: PakasirConfig | None = None) -> PakasirConfig:
    """Return config or raise a user-safe error when payment is not configured."""
    config = config or get_pakasir_config()
    missing = []
    if not config.enabled:
        missing.append("WIZARR_PAKASIR_ENABLED=true")
    if not config.project:
        missing.append("WIZARR_PAKASIR_PROJECT")
    if not config.api_key:
        missing.append("WIZARR_PAKASIR_API_KEY")
    if not config.webhook_token:
        missing.append("WIZARR_PAKASIR_WEBHOOK_TOKEN")
    if missing:
        raise PakasirConfigurationError(
            "Pakasir QRIS belum dikonfigurasi: " + ", ".join(missing)
        )
    return config


def _json_list(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value or [])


def _load_list(value: str | None) -> list[int]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result


def sync_plans_from_env() -> None:
    """Upsert plans from WIZARR_PAKASIR_PLANS_JSON for simple deployments.

    Example:
    [
      {"slug":"monthly","name":"30 Hari","amount":30000,
       "duration_days":30,"server_ids":[1],"library_ids":[1,2]}
    ]
    """
    raw = current_app.config.get("PAKASIR_PLANS_JSON") or os.getenv(
        "WIZARR_PAKASIR_PLANS_JSON", ""
    )
    if not raw:
        return

    try:
        plans = json.loads(raw)
    except json.JSONDecodeError as exc:
        current_app.logger.warning("Invalid WIZARR_PAKASIR_PLANS_JSON: %s", exc)
        return

    if not isinstance(plans, list):
        current_app.logger.warning("WIZARR_PAKASIR_PLANS_JSON must be a JSON array")
        return

    changed = False
    for item in plans:
        if not isinstance(item, dict):
            continue
        slug = str(item.get("slug", "")).strip()
        name = str(item.get("name", slug)).strip()
        try:
            amount = int(item.get("amount"))
            duration_days = int(item.get("duration_days"))
        except (TypeError, ValueError):
            current_app.logger.warning("Skipping invalid Pakasir plan %s", slug or item)
            continue
        if not slug or not name or amount <= 0 or duration_days <= 0:
            current_app.logger.warning(
                "Skipping incomplete Pakasir plan %s", slug or item
            )
            continue

        plan = PakasirPlan.query.filter_by(slug=slug).first()
        if not plan:
            plan = PakasirPlan(slug=slug)
            db.session.add(plan)
        plan.name = name
        plan.amount = amount
        plan.duration_days = duration_days
        plan.server_ids = _json_list(item.get("server_ids", []))
        plan.library_ids = _json_list(item.get("library_ids", []))
        plan.allow_downloads = bool(item.get("allow_downloads", False))
        plan.allow_live_tv = bool(item.get("allow_live_tv", False))
        plan.allow_mobile_uploads = bool(item.get("allow_mobile_uploads", False))
        plan.invite_expires_days = (
            int(item["invite_expires_days"])
            if str(item.get("invite_expires_days", "")).isdigit()
            else 7
        )
        plan.active = bool(item.get("active", True))
        changed = True

    if changed:
        db.session.commit()


def get_active_plans() -> list[PakasirPlan]:
    sync_plans_from_env()
    return (
        PakasirPlan.query.filter_by(active=True)
        .order_by(PakasirPlan.amount.asc())
        .all()
    )


def create_order(plan: PakasirPlan, buyer_email: str | None = None) -> PakasirOrder:
    config = ensure_pakasir_config()
    timestamp = f"{datetime.datetime.now(datetime.UTC):%Y%m%d%H%M%S}"
    order_id = f"WIZARR-{timestamp}-{secrets.token_hex(4).upper()}"
    redirect_url = url_for("qris.order_status", order_id=order_id, _external=True)
    query = urlencode({"order_id": order_id, "qris_only": 1, "redirect": redirect_url})
    payment_url = f"{config.base_url}/pay/{config.project}/{plan.amount}?{query}"
    order = PakasirOrder(
        order_id=order_id,
        project=config.project,
        amount=plan.amount,
        status="pending",
        payment_method="qris",
        payment_url=payment_url,
        buyer_email=buyer_email or None,
        plan=plan,
    )
    db.session.add(order)
    db.session.commit()
    return order


def get_plan_server_ids(plan: PakasirPlan) -> list[int]:
    return _load_list(plan.server_ids)


def get_plan_library_ids(plan: PakasirPlan) -> list[int]:
    return _load_list(plan.library_ids)


class _InviteForm:
    def __init__(self, data: dict[str, Any]):
        self.data = data

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def getlist(self, key: str) -> list[Any]:
        value = self.data.get(key, [])
        if isinstance(value, list):
            return value
        if value is None:
            return []
        return [value]


def _invite_expiry_key(plan: PakasirPlan) -> str:
    days = plan.invite_expires_days
    if days == 1:
        return "day"
    if days == 7:
        return "week"
    if days == 30:
        return "month"
    return "week"


def create_invitation_for_order(order: PakasirOrder) -> Invitation:
    if order.invitation:
        return order.invitation

    plan = order.plan
    form = _InviteForm(
        {
            "server_ids": [str(server_id) for server_id in get_plan_server_ids(plan)],
            "libraries": [str(library_id) for library_id in get_plan_library_ids(plan)],
            "expires": _invite_expiry_key(plan),
            "duration": str(plan.duration_days),
            "unlimited": False,
            "allow_downloads": plan.allow_downloads,
            "allow_live_tv": plan.allow_live_tv,
            "allow_mobile_uploads": plan.allow_mobile_uploads,
        }
    )
    invite = create_invite(form)
    order.invitation = invite
    order.status = "completed"
    order.verified_at = datetime.datetime.now(datetime.UTC)
    db.session.commit()
    return invite


def _parse_pakasir_datetime(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(normalized)
    except ValueError:
        return None


def fetch_transaction_detail(
    order: PakasirOrder, config: PakasirConfig | None = None
) -> dict[str, Any]:
    config = ensure_pakasir_config(config)
    response = requests.get(
        f"{config.base_url}/api/transactiondetail",
        params={
            "project": order.project,
            "amount": order.amount,
            "order_id": order.order_id,
            "api_key": config.api_key,
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise PakasirVerificationError("Invalid Transaction Detail API response")
    return payload


def verify_webhook_and_complete(payload: dict[str, Any]) -> PakasirOrder:
    config = ensure_pakasir_config()
    order_id = str(payload.get("order_id", "")).strip()
    if not order_id:
        raise PakasirVerificationError("Missing order_id")

    order = PakasirOrder.query.filter_by(order_id=order_id).first()
    if not order:
        raise PakasirVerificationError("Unknown order_id")

    order.raw_webhook_payload = json.dumps(payload, default=str)
    db.session.commit()

    if str(payload.get("project", "")).strip() != order.project:
        raise PakasirVerificationError("Project mismatch")
    try:
        amount = int(payload.get("amount"))
    except (TypeError, ValueError) as exc:
        raise PakasirVerificationError("Invalid amount") from exc
    if amount != order.amount:
        raise PakasirVerificationError("Amount mismatch")
    if str(payload.get("status", "")).lower() != "completed":
        raise PakasirVerificationError("Payment is not completed")

    if order.invitation_id and order.status == "completed":
        return order

    detail_payload = fetch_transaction_detail(order, config)
    order.raw_detail_payload = json.dumps(detail_payload, default=str)
    transaction = detail_payload.get("transaction", {})
    if not isinstance(transaction, dict):
        raise PakasirVerificationError("Missing transaction detail")
    if str(transaction.get("project", "")).strip() != order.project:
        raise PakasirVerificationError("Verified project mismatch")
    if str(transaction.get("order_id", "")).strip() != order.order_id:
        raise PakasirVerificationError("Verified order_id mismatch")
    try:
        verified_amount = int(transaction.get("amount"))
    except (TypeError, ValueError) as exc:
        raise PakasirVerificationError("Invalid verified amount") from exc
    if verified_amount != order.amount:
        raise PakasirVerificationError("Verified amount mismatch")
    if str(transaction.get("status", "")).lower() != "completed":
        raise PakasirVerificationError("Verified transaction is not completed")

    order.payment_method = str(
        transaction.get("payment_method") or payload.get("payment_method") or "qris"
    )
    order.completed_at = _parse_pakasir_datetime(
        str(transaction.get("completed_at") or payload.get("completed_at") or "")
    )
    create_invitation_for_order(order)
    return order
