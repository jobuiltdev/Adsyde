# Credit accounting

The append-only credit ledger is the accounting source of truth. Wallet balances are transactional
materializations that can be reconstructed from ledger deltas. Credits are integer units and have
no fixed currency conversion in M7.

## Accounting convention

Each ledger entry records both total-balance and reserved-balance movement:

- grants add a positive balance delta;
- reservations leave total balance unchanged and add a positive reserved delta;
- releases leave total balance unchanged and add a negative reserved delta;
- charges subtract the same positive quantity from total and reserved balances.

Available credits equal total balance minus reserved balance. PostgreSQL constraints require both
stored values to remain nonnegative and reserved credits never to exceed total balance.

Each generation has at most one charge lifecycle. Reservation snapshots the server-controlled
model, duration, rate, quote, and pricing version. Valid transitions are reserved to charged or
released. Stable generation references make reserve, charge, and release operations idempotent.
Wallet and charge rows are locked before mutation, preventing concurrent requests from spending the
same available credits.

Provider submission is queued only after generation and reservation commit. A successfully
validated and privately ingested result is charged within the completion transaction. Definite
failure and confirmed cancellation release the reservation. UNKNOWN retains it; terminal
PROVIDER_STATE_UNRESOLVED releases it because the user received no confirmed result. A later real
provider may require an internal loss process, but users must not be charged based on uncertainty.
Pre-M7 generations have no charge record and remain viewable and unbilled.

Ledger and charge references retain generation UUID snapshots. Their nullable generation links use
SET_NULL, so project deletion cannot erase financial history. Wallet, transaction, and charge
records are protected from user deletion; future account deletion needs an explicit retention and
anonymization policy. Admin views are read-only. Corrections must be compensating entries.

Local and test settings provide a development-only initial grant through the same ledger service.
Production defaults to zero. Staff can grant positive credits with:

    python manage.py grant_credits user@example.com 1000 --reason "Local development"

An optional stable reference makes retries idempotent. There is no self-grant API. Audit stored and
ledger totals without modifying data with:

    python manage.py reconcile_credits

The authenticated wallet and paginated transaction APIs expose only the current user. Generation
options include authoritative development credit quotes; clients cannot submit prices.

## M8 handoff

M8 may add Paystack payment initiation, server-verified webhooks, immutable payment records, and an
idempotent purchase ledger mutation. Payment code must call the M7 ledger service and must never
edit wallet balances directly. Currency conversion, provider economics, payment fees, retries, and
margin remain undecided until provider validation.
