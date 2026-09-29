from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from app.extensions import limiter
from app.models import PakasirOrder, PakasirPlan
from app.services.payments.pakasir import (
    PakasirConfigurationError,
    PakasirVerificationError,
    create_order,
    ensure_pakasir_config,
    get_active_plans,
    get_pakasir_config,
    sync_plans_from_env,
    verify_webhook_and_complete,
)

qris_bp = Blueprint("qris", __name__, url_prefix="/qris")


@qris_bp.route("/")
@limiter.limit("30 per minute")
def plans():
    config = get_pakasir_config()
    try:
        ensure_pakasir_config(config)
        config_error = None
    except PakasirConfigurationError as exc:
        config_error = str(exc)
    plans = get_active_plans() if not config_error else []
    return render_template(
        "qris/plans.html",
        plans=plans,
        config_error=config_error,
        webhook_url=(
            url_for("qris.pakasir_webhook", token=config.webhook_token, _external=True)
            if config.webhook_token
            else None
        ),
    )


@qris_bp.route("/checkout", methods=["POST"])
@limiter.limit("10 per minute")
def checkout():
    try:
        ensure_pakasir_config()
    except PakasirConfigurationError as exc:
        return render_template("qris/error.html", message=str(exc)), 503

    sync_plans_from_env()
    plan_slug = request.form.get("plan_slug", "").strip()
    plan = PakasirPlan.query.filter_by(slug=plan_slug, active=True).first()
    if not plan:
        return render_template("qris/error.html", message="Paket tidak ditemukan."), 404

    order = create_order(plan, request.form.get("email"))
    return redirect(order.payment_url)


@qris_bp.route("/orders/<order_id>")
@limiter.limit("30 per minute")
def order_status(order_id):
    order = PakasirOrder.query.filter_by(order_id=order_id).first_or_404()
    invite_url = None
    if order.invitation:
        invite_url = url_for(
            "public.invite", code=order.invitation.code, _external=True
        )
    return render_template("qris/status.html", order=order, invite_url=invite_url)


@qris_bp.route("/webhooks/pakasir/<token>", methods=["POST"])
@limiter.exempt
def pakasir_webhook(token):
    config = get_pakasir_config()
    if not config.webhook_token or token != config.webhook_token:
        return jsonify({"error": "invalid webhook token"}), 403

    payload = request.get_json(silent=True)
    if payload is None:
        payload = request.form.to_dict()
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid payload"}), 400

    try:
        order = verify_webhook_and_complete(payload)
    except PakasirConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503
    except PakasirVerificationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "failed to verify Pakasir transaction"}), 502

    invite_url = None
    if order.invitation:
        invite_url = url_for(
            "public.invite", code=order.invitation.code, _external=True
        )
    return jsonify(
        {
            "ok": True,
            "order_id": order.order_id,
            "status": order.status,
            "invitation_url": invite_url,
        }
    )
