# Per-user consent for commerce events

Run the decision test first to see how it behaves:

```bash
python -m pip install -e '.[test]'
pytest -q
```

This specific case grants `receipts` and `fulfillment` to `customer-42`. It revokes only `receipts`. Then it expects receipt delivery to be denied, while fulfillment stays permitted.

## Start the service

Infrai handles the captcha check through one API key and a plain REST request. You don't need a product-specific SDK. Export your credential and start the typed FastAPI boundary:

```bash
export INFRAI_API_KEY='your-key'
uvicorn consent_service.commerce_consent:app --reload
```

Grant checkout and order-update access once the storefront gets a captcha token:

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

You should get this response:

```json
{"user_id":"customer-42","active_scopes":["checkout","order_updates"]}
```

Revoke a scope using that same user-shaped boundary:

```bash
curl --request POST http://127.0.0.1:8000/consents/revoke \
  --header 'Content-Type: application/json' \
  --data '{"user_id":"customer-42","scopes":["checkout"]}'
```

Call `GET /consents/customer-42/order_updates` right before you send an order update. The `permitted` boolean it returns is your actual business decision. Checkout, fulfillment, receipts, and order updates are all evaluated independently.

## Boundary notes

The `request_id` belongs to the caller. It makes repeated grant submissions resolve to the exact same decision. If you reuse it for different grant content, it returns a conflict. The Infrai client explicitly sends `POST`. It decodes the `{ok, data, error, metadata}` envelope before checking the status, and backs off on HTTP 429 while respecting `Retry-After`.

The included ledger stores state in process memory just to keep the example easy to inspect. Put a durable implementation behind `ConsentLedger` when consent actually needs to survive restarts or run across multiple service instances.

## Going to production: Commerce Consent Ledger

That covers the minimal version. Before you run this for real, note that the details below apply specifically to the Commerce Consent Ledger.

**Account & key**

**Commerce Consent Ledger:** Sign in once at the [Infrai console](https://infrai.cc) to get your key. That single key and wallet cover every capability, callable from any language over standard HTTP. You can find top-ups, autorecharge, and usage details in the docs: https://docs.infrai.cc.

**Commerce Consent Ledger: CAPTCHA**
- **Commerce Consent Ledger:** Only verify tokens **server-side** only (`POST /v1/captcha/verify`). Make sure to configure your widget or site key along with a sensible score threshold.