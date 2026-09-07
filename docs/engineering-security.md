# Engineering and Security Rules

This document defines implementation requirements for later milestones. Values affected by traffic, provider constraints, infrastructure, regulation, or observed abuse remain configurable and must be validated before production.

## Local development and configuration

- Development and automated tests must run without paid credentials, paid API calls, live payments, or real video generation.
- External boundaries require deterministic fakes or mocks. Network-dependent tests are separate and opt-in.
- Secrets come from the runtime environment or an approved secret manager in production. They do not belong in source code, frontend bundles, logs, ordinary database fields, or committed environment files.
- Safe example configuration may document variable names with inert values only. Startup validates required settings and rejects unsafe production defaults.
- Development uses local media storage initially. Storage, email, payment, and generation integrations are selected through explicit configuration.

## Authentication controls

- Use Django's maintained password hashing framework with an intentionally configured production hasher and upgrade path; never implement password cryptography directly.
- Email verification and password reset use single-purpose, random, one-time, expiring tokens. Store a cryptographic digest when feasible, invalidate tokens after use or replacement, and never log them.
- Registration, login, reset, and verification responses resist account enumeration through consistent public messages and comparable behavior. Delivery side effects remain conditional internally.
- Authentication failures and sensitive account changes create safe audit events containing actor/account identifiers when known, coarse network context, outcome, reason category, and timestamp—not credentials or tokens.
- The browser authentication design must document its CSRF and XSS tradeoffs before M2. If cookies carry authentication, use `Secure`, `HttpOnly`, and appropriate `SameSite` settings with CSRF protection. If refresh tokens exist, rotate them, detect reuse, support revocation, and define logout invalidation.
- Password and email changes invalidate relevant sessions and outstanding recovery tokens. Users should be able to review and revoke active devices/sessions where practical.

## Endpoint-specific rate limiting

Rate limits are policy groups, not a universal number. Enforcement should use Redis-backed counters in deployed environments and support more than one key per request. Exact production values are deferred until threat modeling and load/abuse observations; safe configurable defaults and tests are required before exposure.

| Endpoint class | Candidate keys | Policy behavior |
|---|---|---|
| Registration | IP/subnet, normalized email digest, device signal where lawful | Low burst; longer-window cap; enumeration-safe response |
| Login | IP/subnet plus account/email digest | Small burst and progressive cooldown; avoid permanent attacker-triggered lockout |
| Password-reset request | IP/subnet plus account/email digest | Strict send cap and daily window; identical public response |
| Password-reset completion | token identifier plus IP and account | Tight attempt cap; invalidate on success and suspicious repeated failure |
| Verification resend | user/account plus IP | Cooldown between sends and longer-window delivery cap |
| Token refresh | session/token family plus user and IP | Moderate normal allowance; detect replay and abnormal bursts |
| Generation creation | authenticated user, project/account, and IP | Low burst; concurrent-job and spend/reservation checks |
| Retry or regeneration | user plus generation/project and IP | Stricter than reads; bounded attempts and idempotency required |
| Uploads | user plus IP | Request and byte-volume quotas; concurrent-upload and storage quotas |
| Payment creation | user/account plus IP and payment reference | Low burst; idempotency key required; amount/business validation |
| Sensitive account operations | user/session plus IP | Low burst, recent authentication where appropriate, audit event |
| Expensive or abuse-prone endpoints | user/API subject plus IP, route, and cost class | Weighted budgets, concurrency bounds, and backpressure |

Limits should return normalized `429` responses with safe retry guidance. Reverse-proxy addresses are trusted only through an explicit proxy configuration. Policies define behavior when the counter store is unavailable: security- and money-sensitive writes should normally fail closed or degrade to a conservative local bound, while low-risk reads may fail open. Bypass and administrative exceptions must be narrow, time-bound, and audited.

## API and browser security

- Production assumes HTTPS and sets HSTS after deployment validation, content-type sniffing protection, a restrictive referrer policy, frame-ancestor protection, and a tested Content Security Policy.
- CORS uses an explicit production origin allowlist; credentials are never combined with wildcard origins. Preflight methods and headers are minimal.
- CSRF protection follows the selected credential transport and is tested for every state-changing browser request.
- The API performs serializer/domain validation and authorization server-side. Frontend checks improve usability only.
- Object access checks ownership or granted permission on every request; identifiers are not authorization.
- Public errors use stable codes and safe messages with correlation identifiers. Stack traces, SQL details, provider payloads, and internal exception text remain server-side.
- Request sizes, parser types, pagination, timeouts, and expensive query shapes have explicit bounds. Administrative interfaces use separate authorization and stronger operational controls.
- Dependencies are pinned through lockfiles, reviewed, and scanned in continuous integration once introduced. Security updates receive priority without unreviewed automatic production deployment.

## Database integrity and concurrency

- Use foreign keys for relationships and database uniqueness/check constraints for invariants such as idempotency keys, external references, valid amounts, and permitted field combinations.
- Critical workflows use transactions. Credit operations and other concurrent balance/account changes use row locks, serializable techniques, or compare-and-set semantics appropriate to the contention model.
- Application validation provides useful errors, but correctness must survive bypassing the application layer.
- Migrations are reviewed for locking, data backfill, reversibility, and deploy ordering. Destructive schema changes require staged rollout and recovery planning.
- Ledger entries are append-only. Corrections use compensating entries; deletion or in-place amount edits are prohibited through normal application paths.

## Payments and credit safety

- Money uses integer minor units and credits use an explicitly defined integer unit; floating-point arithmetic is prohibited.
- Every payment initiation and ledger mutation has an idempotency key scoped by operation and owner. Uniqueness is database-enforced.
- Webhook handlers verify signatures over the raw body before parsing or mutating state, reject stale/invalid events as policy requires, and safely acknowledge already-processed duplicates.
- Payment status is verified server-to-server before allocation. Allocation and payment transition occur atomically; reconciliation detects missing, duplicate, or inconsistent records.
- Generation reservation checks available credit and records the reservation atomically. Settlement or refund references that reservation and cannot occur twice.
- Administrative adjustments require a reason, actor identity, authorization, immutable audit trail, and optional approval threshold to be defined before production.

## Generation reliability

- Persist the generation and immutable specification snapshot before queuing or contacting a provider.
- Implement an explicit transition service and database-protected state changes. Do not assign lifecycle states ad hoc.
- Queue tasks, submissions, callbacks, polling updates, settlements, and notifications are idempotent independently.
- Keep provider attempts separate from the customer-visible generation. Bounded retries may create new attempts without losing earlier evidence.
- Duplicate and delayed callbacks cannot regress terminal state or duplicate credits/results. Unknown, malformed, or contradictory responses become normalized failures or review cases rather than uncaught exceptions.
- Timeouts distinguish an unknown provider outcome from a confirmed failure. Reconciliation resolves stuck work after worker crashes or outages.
- Logs and user errors expose internal generation identifiers and safe categories, not credentials or unredacted vendor payloads.

## Upload and media security

- Enforce per-file, request, account, and storage quotas. Validate declared type, allowed extension, and detected content signature; decode images where feasible to reject malformed or polyglot content.
- Generate storage keys server-side. Sanitize display filenames, prevent path traversal and collisions, and never use user filenames as executable paths.
- Keep uploads private by default. Downloads use authorization checks or short-lived scoped URLs. Asset records enforce user/project ownership.
- Store media outside executable/static application paths and serve it with safe content types and download headers where appropriate.
- Image processing is resource-bounded and isolated where practical. Metadata is removed or retained according to an explicit privacy requirement.
- Future malware scanning and quarantine policy should be evaluated before accepting broader media formats or public sharing.

## Logging, audit, and privacy

- Application logs are structured and include timestamp, severity, service, environment, correlation identifier, event name, and safe object identifiers.
- Never log passwords, reset/verification tokens, session or authentication tokens, API secrets, provider credentials, webhook secrets, complete payment credentials, or unredacted authorization headers.
- Central redaction covers request bodies, headers, query parameters, and provider payloads. Access to production logs is restricted and audited.
- Security-sensitive actions create append-only audit events separate from diagnostic logs. Event types include authentication outcomes, session revocation, credential/contact changes, payment decisions, credit adjustments, permission changes, and administrative actions.
- Define purpose, access, retention, deletion, and backup treatment for personal data before production. Collect only data required for the product or security purpose.

## Testing expectations

Later milestones must add risk-proportionate tests including:

- unit tests for domain policies and normalization;
- API integration and authorization tests;
- database constraint and transaction tests against PostgreSQL;
- authentication enumeration, token expiry/reuse, logout, and abuse tests;
- endpoint rate-limit tests across relevant IP and user keys, including counter-store failure behavior;
- generation transition, retry, crash recovery, timeout, delayed/duplicate callback, and malformed-response tests;
- idempotency tests for every externally retried write;
- payment signature, duplicate webhook, verification, pending/failure, and reconciliation tests;
- concurrent reservation, settlement, refund, and balance tests;
- upload size, content, filename, ownership, quota, and authorization tests;
- provider failure simulations using only the realistic mock.

Tests should be deterministic, isolate state, avoid real credentials, and never require paid services. Security controls need negative tests that demonstrate prohibited transitions and access are rejected.
