import hashlib
import json

from app.extensions import db
from app.models import (
    AdminAccount,
    ApiKey,
    Invitation,
    MediaServer,
    PakasirOrder,
    PakasirPlan,
)
from app.services.payments import pakasir
from app.services.payments.pakasir import create_order, verify_webhook_and_complete


def _configure(app):
    app.config.update(
        PAKASIR_ENABLED=True,
        PAKASIR_PROJECT="depodomain",
        PAKASIR_API_KEY="secret-key",
        PAKASIR_WEBHOOK_TOKEN="receiver-token",
        PAKASIR_BASE_URL="https://app.pakasir.test",
    )


def _api_key(session):
    admin = AdminAccount(username="qrisadmin")
    admin.set_password("testpass")
    session.add(admin)
    session.flush()
    raw_key = "qris_api_key_12345"
    session.add(
        ApiKey(
            name="QRIS API Key",
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            created_by_id=admin.id,
            is_active=True,
        )
    )
    session.commit()
    return raw_key


def _server_and_plan(session):
    server = MediaServer(
        name="Test Plex",
        server_type="plex",
        url="http://plex.test",
        api_key="token",
        verified=True,
    )
    session.add(server)
    session.commit()
    plan = PakasirPlan(
        slug="monthly",
        name="30 Hari",
        amount=30000,
        duration_days=30,
        server_ids=json.dumps([server.id]),
        library_ids=json.dumps([]),
        active=True,
    )
    session.add(plan)
    session.commit()
    return server, plan


def test_create_order_builds_qris_only_payment_url(app, session):
    _configure(app)
    _, plan = _server_and_plan(session)

    with app.test_request_context("/qris/"):
        order = create_order(plan, "buyer@example.com")

    assert order.status == "pending"
    assert order.amount == 30000
    assert "qris_only=1" in order.payment_url
    assert "order_id=" in order.payment_url
    assert order.buyer_email == "buyer@example.com"


def test_verified_webhook_creates_single_invitation(app, session, monkeypatch):
    _configure(app)
    _, plan = _server_and_plan(session)

    with app.test_request_context("/qris/"):
        order = create_order(plan)

    def fake_fetch_transaction_detail(order, config=None):
        return {
            "transaction": {
                "project": "depodomain",
                "order_id": order.order_id,
                "amount": 30000,
                "status": "completed",
                "payment_method": "qris",
                "completed_at": "2024-09-10T08:07:02.819+07:00",
            }
        }

    monkeypatch.setattr(
        pakasir, "fetch_transaction_detail", fake_fetch_transaction_detail
    )

    payload = {
        "project": "depodomain",
        "order_id": order.order_id,
        "amount": 30000,
        "status": "completed",
        "payment_method": "qris",
    }
    completed = verify_webhook_and_complete(payload)
    first_invitation_id = completed.invitation_id

    assert completed.status == "completed"
    assert completed.invitation.duration == "30"
    assert completed.invitation.unlimited is False
    assert Invitation.query.count() == 1

    replayed = verify_webhook_and_complete(payload)

    assert replayed.invitation_id == first_invitation_id
    assert Invitation.query.count() == 1


def test_webhook_rejects_wrong_receiver_token(app, client, session):
    _configure(app)
    _server_and_plan(session)

    response = client.post(
        "/qris/webhooks/pakasir/wrong-token",
        json={"order_id": "WIZARR-UNKNOWN"},
    )

    assert response.status_code == 403


def test_webhook_rejects_amount_mismatch_before_invite(app, session, monkeypatch):
    _configure(app)
    _, plan = _server_and_plan(session)

    with app.test_request_context("/qris/"):
        order = create_order(plan)

    def fake_fetch_transaction_detail(order, config=None):
        raise AssertionError("Transaction Detail API should not be called")

    monkeypatch.setattr(
        pakasir, "fetch_transaction_detail", fake_fetch_transaction_detail
    )

    payload = {
        "project": "depodomain",
        "order_id": order.order_id,
        "amount": 29999,
        "status": "completed",
    }

    try:
        verify_webhook_and_complete(payload)
    except pakasir.PakasirVerificationError as exc:
        assert "Amount mismatch" in str(exc)
    else:
        raise AssertionError("amount mismatch should fail verification")

    saved_order = PakasirOrder.query.filter_by(order_id=order.order_id).first()
    assert saved_order.invitation is None
    assert Invitation.query.count() == 0


def test_qris_api_exposes_plan_and_creates_order(app, client, session):
    _configure(app)
    _, plan = _server_and_plan(session)
    api_key = _api_key(session)

    plans_response = client.get("/api/qris/plans", headers={"X-API-Key": api_key})

    assert plans_response.status_code == 200
    assert plans_response.json["count"] == 1
    assert plans_response.json["plans"][0]["slug"] == plan.slug

    order_response = client.post(
        "/api/qris/orders",
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json={"plan_slug": plan.slug, "buyer_email": "buyer@example.com"},
    )

    assert order_response.status_code == 201
    assert order_response.json["order"]["payment_url"]
    assert "qris_only=1" in order_response.json["order"]["payment_url"]

    order_id = order_response.json["order"]["order_id"]
    status_response = client.get(
        f"/api/qris/orders/{order_id}", headers={"X-API-Key": api_key}
    )

    assert status_response.status_code == 200
    assert status_response.json["order_id"] == order_id


def test_swagger_includes_qris_namespace(app, client):
    response = client.get("/api/swagger.json")

    assert response.status_code == 200
    assert "/qris/plans" in response.json["paths"]
    assert "/qris/orders" in response.json["paths"]
