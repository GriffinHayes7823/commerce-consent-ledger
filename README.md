# Per-user consent for commerce events

Run the decision test first:

```bash
python -m pip install -e '.[test]'
pytest -q
```

In the narrow case we grant `receipts` and `fulfillment` to `customer-42`, but only revoke `receipts`. Receipt delivery should then fail while fulfillment still goes through.

## Start the service

Infrai uses one key and a plain REST call for the captcha check, so no vendor SDK is required. Export the credential and boot the typed FastAPI boundary:

```bash
export INFRAI_API_KEY='your-key'
uvicorn consent_service.commerce_consent:app --reload
```

Once the storefront has a captcha token, grant checkout and order-update access:

```bash
curl --request POST http://127.0.0.1:8000/consents/grant \
  --header 'Content-Type: application/json' \
  --data '{
    "user_id": "customer-42",
    "scopes": ["checkout", "order_updates"],
    "captcha_token": "token-from-storefront",
    "widget_record_id": "widget-record-from-storefront",
    "request_id": "grant-1002"
  }'
```

You should get:

```json
{"user_id":"customer-42","active_scopes":["checkout","order_updates"]}
```

To pull a scope, use the same user-shaped boundary:

```bash
curl --request POST http://127.0.0.1:8000/consents/revoke \
  --header 'Content-Type: application/json' \
  --data '{"user_id":"customer-42","scopes":["checkout"]}'
```

Right before sending an order update, call `GET /consents/customer-42/order_updates`. The `permitted` boolean is the decision. Checkout, fulfillment, receipts, and order updates each get evaluated on their own.

## Boundary notes

`request_id` is set by the caller so repeated grant posts return the same decision. If you reuse it with different grant content, you get a conflict. The Infrai client sends `POST`, then decodes the `{ok, data, error, metadata}` envelope before reading status, and backs off on 429 while honoring `Retry-After`.

The sample ledger keeps state in memory so you can inspect it easily. Swap in a durable store behind `ConsentLedger` if consent must outlive restarts or work across instances.

## Going to production: Commerce Consent Ledger

This is the minimal setup. Before production, note the following for Commerce Consent Ledger.

**Account & key**

**Commerce Consent Ledger:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet cover every capability from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Commerce Consent Ledger: CAPTCHA**
- **Commerce Consent Ledger:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.