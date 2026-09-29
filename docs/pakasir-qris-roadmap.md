# Pakasir QRIS Integration Roadmap

Pakasir does not expose a dashboard webhook secret. The integration therefore must not trust webhook payloads by themselves.

## Phase 1 - Receiver hardening

- Use a merchant-generated unguessable webhook URL token: `/qris/webhooks/pakasir/<token>`.
- Store the token in `WIZARR_PAKASIR_WEBHOOK_TOKEN` and paste the full URL into Pakasir's project dashboard.
- Treat this token as a first gate only; it is not a replacement for payment verification.

## Phase 2 - Local order ledger

- Create a pending `pakasir_order` before redirecting the customer to Pakasir.
- Persist expected `project`, `amount`, `order_id`, selected plan, and payment URL.
- Reject webhooks whose `project`, `amount`, `order_id`, or `status` do not match the local order.

## Phase 3 - Server-side verification

- On webhook receipt, call Pakasir Transaction Detail API with the private API key.
- Only complete the order if Transaction Detail returns the same `project`, `amount`, `order_id`, and `status=completed`.
- Never create Wizarr invitations from browser redirects alone.

## Phase 4 - Idempotent invite creation

- Create exactly one Wizarr invitation per completed Pakasir order.
- Replayed webhooks return the existing invitation instead of creating another one.
- Set Wizarr `duration` from the selected package so the created media user expires after the paid subscription period.

## Phase 5 - Operator configuration

Required environment variables:

```env
WIZARR_PAKASIR_ENABLED=true
WIZARR_PAKASIR_PROJECT=your-pakasir-slug
WIZARR_PAKASIR_API_KEY=your-project-api-key
WIZARR_PAKASIR_WEBHOOK_TOKEN=generate-a-long-random-value
WIZARR_PAKASIR_PLANS_JSON=[{"slug":"monthly","name":"30 Hari","amount":30000,"duration_days":30,"server_ids":[1]}]
```

Optional:

```env
WIZARR_PAKASIR_BASE_URL=https://app.pakasir.com
```

## Phase 6 - Customer flow

1. Customer opens `/qris/` and selects a package.
2. Wizarr creates a local pending order.
3. Customer is redirected to Pakasir with `qris_only=1`.
4. Pakasir posts a webhook to Wizarr.
5. Wizarr verifies the order with Transaction Detail API.
6. Wizarr creates `/j/<code>` only after verification succeeds.


## Phase 7 - Wizarr API / Swagger surface

The customer pages remain available at `/qris/`, but operators and external storefronts can also use the documented Wizarr API:

- `GET /api/qris/plans` lists configured QRIS plans.
- `POST /api/qris/plans` creates or updates a QRIS plan.
- `POST /api/qris/orders` creates a Pakasir checkout order for a plan and returns the Pakasir payment URL.
- `GET /api/qris/orders/{order_id}` returns order status and the invitation URL after payment verification.

These API routes use the existing Wizarr `X-API-Key` authentication and appear in `/api/swagger.json`. Pakasir webhooks still use `/qris/webhooks/pakasir/<token>` because Pakasir cannot send the Wizarr API key and must be verified through the receiver token plus Transaction Detail API.
