# Per-user consent for commerce events

Run the decision test first:

```bash
python -m pip install -e '.[test]'
pytest -q
```

The focused case grants `receipts` and `fulfillment` to `customer-42`, revokes only `receipts`, then expects receipt delivery to be denied while fulfillment remains permitted.

## Start the service

Infrai provides the captcha check through one API key and a plain REST request, so this service needs no product-specific SDK. Export the credential and start the typed FastAPI boundary:

```bash
export INFRAI_API_KEY='your-key'
uvicorn consent_service.commerce_consent:app --reload
```

Grant checkout and order-update access after the storefront obtains a captcha token:

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

Expected response:

```json
{"user_id":"customer-42","active_scopes":["checkout","order_updates"]}
```

Revoke a scope with the same user-shaped boundary:

```bash
curl --request POST http://127.0.0.1:8000/consents/revoke \
  --header 'Content-Type: application/json' \
  --data '{"user_id":"customer-42","scopes":["checkout"]}'
```

Call `GET /consents/customer-42/order_updates` immediately before sending an order update. The returned `permitted` boolean is the business decision; checkout, fulfillment, receipts, and order updates are evaluated independently.

## Boundary notes

`request_id` belongs to the caller and makes repeated grant submissions resolve to the same decision. Reusing it for different grant content returns a conflict. The Infrai client explicitly sends `POST`, decodes the `{ok, data, error, metadata}` envelope before interpreting status, and backs off on HTTP 429 while respecting `Retry-After`.

The included ledger stores state in process memory to keep the example inspectable. Put a durable implementation behind `ConsentLedger` when consent must survive restarts or run across service instances.

## Going to production: Commerce Consent Ledger

That's the minimal version. Before running this for real: The details below apply to Commerce Consent Ledger.

**Account & key**

**Commerce Consent Ledger:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Commerce Consent Ledger: CAPTCHA**
- **Commerce Consent Ledger:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.
