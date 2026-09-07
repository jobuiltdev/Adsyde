# Product and Architecture

## Product boundary

Adsyde helps businesses and creators turn an advertising intent into a generated video advertisement. The initial market focus is Nigeria, including a Paystack-first future payment path, while the domain model should not prevent broader markets later.

V1 is not a timeline editor, campaign manager, publishing platform, team workspace, public developer API, model-training product, influencer platform, or advanced campaign analytics suite. Native mobile applications, collaborative editing, scheduled posting, direct social-network posting, and simultaneous support for many providers are also outside V1. Boundaries should remain extensible without introducing abstractions for these features now.

## Creation experiences

### Guided Ad Builder

The guided flow will collect structured answers such as the advertised item, offer, audience, desired style, destination platform, and reference images. It will translate those answers into a normalized ad specification and a proposed generation prompt. Before generation, the user can inspect and edit that prompt.

### Prompt Studio

Prompt Studio will accept a user-authored prompt plus duration, aspect ratio, references, quality or model tier, and advanced controls. Prompt handling has two explicit modes:

- `EXACT`: preserve the submitted prompt as written.
- `ENHANCE`: produce a suggested or derived prompt while retaining the original.

The selected mode, original prompt, effective prompt, and relevant transformation provenance must be stored separately. An omitted choice must never imply permission to rewrite a custom prompt.

## Normalized creation model

Both experiences produce a versioned Ad Specification. A future schema should represent at least:

- creation mode and schema version;
- product, offer, audience, style, platform, and creative intent;
- original and effective prompts with the explicit prompt-handling mode;
- duration, aspect ratio, quality tier, and supported advanced controls;
- owned reference-asset identifiers rather than public URLs;
- moderation context and user-confirmed settings.

Specifications should be immutable snapshots once attached to a generation. Editing creates a new version so generation history remains reproducible and auditable.

```text
Guided Ad Builder ─┐
                   ├─> versioned Ad Specification ─> Generation Engine
Prompt Studio ─────┘                                  │
                                                      ├─> Provider Contract
                                                      └─> Generated Media
```

The engine owns lifecycle rules, persistence, retries, reservations, and result normalization. Provider adapters translate only between Adsyde concepts and vendor protocols.

## Planned system shape

- **Frontend:** Next.js, TypeScript, and Tailwind CSS. It presents workflows but is not authoritative for validation, authorization, balances, generation state, or payment state.
- **API:** Python, Django, and Django REST Framework. It owns domain rules, authorization, persistence, and public API contracts.
- **Database:** PostgreSQL is the system of record for users, specifications, generations, assets, ledger entries, payments, and audit records.
- **Async work:** Celery with Redis will run provider submissions, polling, callbacks, retries, and media post-processing. Tasks must be idempotent and safe after worker crashes.
- **Storage:** local private storage in development behind a storage interface; S3-compatible object storage may be configured later. Database records store ownership and metadata, not raw media.
- **Deployment direction:** the frontend remains compatible with Vercel; the API, worker, PostgreSQL, and Redis remain compatible with Railway or an equivalent platform. M0 makes no deployment or vendor commitment.

Service separation is not required initially. A modular monolith with independently runnable web and worker processes keeps transactions and domain boundaries clear without premature distributed-system overhead.

## Domain boundaries

These are logical modules, not a requirement to create one Django application per row.

| Domain | Responsibility | Important boundaries |
|---|---|---|
| Accounts | Identity, credentials, verification, sessions, preferences | Does not own billing or project authorization rules |
| Projects | User-owned work, ad specifications, revisions | References assets and generations by stable identifiers |
| Assets | Upload metadata, ownership, validation, storage lifecycle | Storage implementation is replaceable; media is never executable |
| Generations | Requests, lifecycle, attempts, orchestration, results | Owns state transitions; never exposes vendor state directly |
| Providers | Contract, adapters, capability discovery, error mapping | Contains vendor-specific payloads and credentials |
| Credits | Append-only ledger, reservations, settlements, refunds | Balance is derived or safely cached, never the only source of truth |
| Billing | Payment intents, verification, webhook processing, reconciliation | Client success is informational, not authoritative |
| Templates | Reusable guided inputs and specification defaults | Cannot bypass validation or prompt-consent rules |
| Moderation | Policy decisions, rejection reasons, review status | Separates internal/provider decisions from safe user messages |
| Notifications | Delivery requests and status | Consumes domain events; does not decide business outcomes |
| Audit and analytics | Security audit events and product measurements | Redacts sensitive values and separates operational logs from audits |

M1 should create only modules required by its scope. Further splits should follow transactional boundaries and observed complexity.

## Provider contract

A future provider adapter must be able to:

- submit a validated provider-neutral request and return a stable external reference;
- retrieve and normalize status;
- cancel when the provider supports cancellation;
- retrieve result metadata or media safely;
- estimate internal cost without defining the customer price;
- expose capabilities without leaking vendor choices into product records;
- convert transport, timeout, moderation, quota, malformed-response, and outage failures into stable internal error categories.

Provider calls occur only after a persistent generation and attempt record exists. Raw provider request/response data, if retained for diagnosis, must be access-controlled, redacted, size-limited, and governed by a retention policy.

The first implementation will be a deterministic, configurable mock. It must simulate queued, processing, success, failure, timeout, content rejection, outage, malformed responses, delayed callbacks, and duplicate callbacks. Automated tests and ordinary local development must use the mock and local assets.

Provider selection, production limits, and pricing are deferred to M6R because market capability and costs are volatile. Product-facing quality tiers should map through configuration rather than embed provider model names.

## Generation lifecycle

A generation is created transactionally before any external call. Its initial lifecycle is:

```text
DRAFT -> QUEUED -> SUBMITTED -> PROCESSING -> COMPLETED
   │        │          │             │
   └────────┴──────────┴─────────────> FAILED
            └──────────┴─────────────> CANCELLED
```

The exact transition matrix and rules will be formalized with implementation. Terminal states cannot move without an explicit compensating workflow. Every transition records its prior state, next state, source, timestamp, and safe reason. Database locking or compare-and-set updates prevent concurrent invalid transitions.

Each submission has an internal idempotency key and a separate provider attempt record. Callback identities and processed event identifiers are unique. Polling and callbacks converge through the same transition service. Retry policy is bounded, configurable, jittered where appropriate, and distinguishes retriable transport failures from permanent content or validation failures. A reconciliation process detects stuck or ambiguous attempts after crashes and timeouts.

## Credits and billing model

Credits use an immutable, append-only ledger. Entries include a unique idempotency key, account, event type, signed amount, currency or credit unit where relevant, related business object, timestamp, and audit metadata. Expected event types include purchase, promotion, generation reservation, settlement, refund, and administrative adjustment.

Reservations prevent double-spend while a generation is in flight. Reservation, settlement, and refund operations run inside database transactions with row-level locking or an equivalent concurrency control. Constraints prevent duplicate external events and invalid amounts. A cached balance may exist for performance only if it is reconciled against the ledger and updated atomically.

Paystack integration is deferred. Its future boundary requires signed-webhook verification using the raw request body, unique event/reference handling, server-to-server verification, atomic credit allocation, replay protection, pending/failed state handling, and reconciliation. Browser-reported success never allocates credits.

## Deferred decisions

The following require evidence from later milestones and remain configurable or unresolved:

- production generation provider and fallback policy;
- provider model-to-quality-tier mapping and measured cost;
- exact duration, aspect-ratio, file-size, and quota limits;
- production endpoint rate values and Redis topology;
- token versus server-side session details for browser authentication;
- production object-storage, deployment, email, monitoring, and error-reporting vendors;
- retention periods, data residency requirements, and applicable compliance policy;
- whether domain growth justifies service extraction from the modular monolith.

These decisions must preserve the stated contracts and invariants rather than reshape customer workflows around a vendor.
