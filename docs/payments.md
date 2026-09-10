# Nigerian payment architecture

M8 adds test-mode-first Paystack architecture for NGN credit purchases. Package prices are integer
kobo values and development commercial placeholders. They do not define a permanent currency to
credit conversion.

The server owns the enabled package catalog and snapshots package key, display name, credits,
currency, and amount on every payment. Clients submit only a package key and an initialization
identity. The unique user-plus-idempotency-key constraint prevents double clicks and request retries
from creating multiple intents, while a new key permits an intentional later purchase.

The preferred checkout is a top-level redirect to the server-validated Paystack checkout host. No
provider script or public key is loaded in the browser. A browser return is UX context only: the
return page asks the backend to verify and shows a confirming state until the normalized payment is
terminal. Query parameters never prove payment.

## Trust and accounting

Signed webhooks use Paystack's SHA-512 HMAC over the untouched request body. Missing, invalid, or
body-mismatched signatures are rejected. Event-body fingerprints provide durable deduplication.
Only charge.success triggers verification; unsupported events and unknown references are safe
no-ops.

Server verification requires an exact stored reference, integer amount, NGN currency, success
status, and verified account email. Any mismatch enters review-required and never credits
automatically. Provider unavailability stays verification-required rather than failed. Success is
never downgraded by a later event.

Crediting locks the Payment and uses the M7 ledger purchase service in the same PostgreSQL
transaction. The stable payment UUID purchase reference guarantees one PURCHASE entry across
webhook, browser return, reconciliation, retries, and concurrent workers. Payment code never edits
wallet balances.

The fake local/test provider is deterministic and makes no network request. The isolated Paystack
client uses the secret key from settings, explicit initialization/verification timeouts, bounded
single requests, and normalized responses. Payments are disabled by default. Production enablement
requires an HTTPS callback and an explicit test secret; live keys are not accepted by the current
configuration.

Use the read-only audit and bounded reconciliation entry points:

    python manage.py audit_payments
    python manage.py reconcile_payments --pending
    python manage.py reconcile_payments --reference adsyde_reference

Admin payment and event records are read-only. User deletion is protected, and credited payment
records do not cascade away. Full provider payloads, card data, authorization details, signatures,
and secrets are never stored or logged.

External refunds, chargebacks, disputes, tax invoices, production payment activation, stale-payment
scheduling, and live webhook delivery remain deferred. Future reversals require a controlled
compensating ledger policy that cannot create negative user balances.

## M9 handoff

M9 may build the Guided Ad Builder on the stable purchase, wallet, reservation, generation, and
charge flow. It must not change payment or ledger invariants and must stop before real provider or
production-payment work.
