# Provider integration readiness

Adsyde selects the enabled generation provider server-side. Authenticated clients read non-secret
model, ratio, and duration choices from the generation-options API; they cannot select an adapter.
Each adapter exposes a capability declaration and model catalog, then maps provider behavior into
normalized submission, status, reconciliation, callback, and result descriptors.

## Submission and retry policy

The generation UUID-derived external reference remains stable for every attempt.

| Provider capability | Definite transient failure | Ambiguous acceptance |
| --- | --- | --- |
| Native idempotency | Bounded retry with the same key | Reconcile; any later retry must reuse that key |
| External-reference lookup | Retry only when definitely unaccepted | Look up the stable reference first |
| Neither | Retry only when definitely unaccepted | Never resubmit automatically |

Provider errors are normalized into invalid request, content rejection, unsupported option,
configuration, unavailable, rate limited, network/timeout, ambiguous acceptance, malformed
response, unknown job, generation failure, cancellation failure, and result-fetch failure. Tasks
make bounded decisions through the central retry policy. An unknown generation records when
uncertainty began and each reconciliation attempt. Exhaustion ends as FAILED with
PROVIDER_STATE_UNRESOLVED; future billing must treat that result as requiring review, not proof that
external work did or did not occur.

Cancellation records request and provider-confirmation timestamps. A provider without native
cancellation never reports external cancellation as confirmed. Local terminal states remain
authoritative when late events arrive.

## Callbacks and results

Callback adapters own signature verification and payload mapping. The mock callback uses an
environment-provided HMAC secret, signed timestamp, bounded clock tolerance, minimal normalized
payload, and provider-plus-event-ID deduplication. Replays and late terminal events do not repeat
output writes or change terminal state. Signatures, prompts, raw payloads, and private result
locations are not logged.

Adapters return result descriptors; Adsyde ingests media into private Django storage. Ingestion
checks declared and actual size, configured MIME allowlists, basic MP4 signatures, and idempotency.
Network result retrieval is disabled in M6. A future downloader must require HTTPS and
provider-specific host allowlists, reject credentials, private/link-local/loopback destinations and
unsafe redirects, re-check DNS at connection time, stream through byte limits, enforce separate
timeouts, and verify content type and media signature.

Provider selection, enablement, operation-specific timeouts, result limits, allowed future result
hosts, and the mock callback secret are environment controlled. The mock adapter needs no
credential and makes no network request. Reference-image transport remains deferred because M5
selections are editing context only; adding persistence before roles and historical deletion policy
are defined would create a misleading contract.

## M6R handoff

M6R should research current providers; compare API access, usable-ad cost, quality, latency,
reference-image support, commercial terms, moderation, idempotency, reconciliation, and callbacks;
choose one provider; implement only its adapter, configuration, mappings, and signature verifier;
add credentials through secure environment configuration; and run a small controlled paid
evaluation before deciding whether to keep it. Credits, billing, automatic failover, and broader
product features remain separate milestones.
