# Milestone Roadmap

Each milestone begins only after the preceding scope is reviewed. Paid services are not required for development or automated tests.

| Milestone | Outcome |
|---|---|
| **M0 — Product and architecture foundation** | Product boundaries, architecture, security requirements, repository hygiene, and roadmap. No application scaffolding. |
| **M1 — Backend foundation** | Django 5.2 LTS and DRF foundation, PostgreSQL configuration, environment-aware settings, operational endpoints, structured logging, scoped throttling, tests, and a minimal custom user model. |
| **M2 — Authentication and accounts** | Email/password accounts, verification, reset, safe session or token lifecycle, endpoint-specific throttling, and authentication audit events. |
| **M3 — Projects and assets** | Project ownership, versionable creation inputs, secure local uploads, validation, authorization, quotas, and storage abstraction. |
| **M4 — Generation engine and mock provider** | Persistent state machine, async orchestration, provider contract, deterministic mock, idempotency, retries, and failure simulations. |
| **M5 — Prompt Studio and generation UI** | Advanced prompt workflow, explicit exact/enhance choice, controls, references, generation submission, and status/history UI. |
| **M6 — Provider integration readiness** | Adapter readiness, capability mapping, callback/polling paths, operational recovery, and complete failure simulation. No paid generation. |
| **M6R — Real provider validation (deferred)** | Current market and pricing research, provider selection, controlled integration, real generations, quality evaluation, and measured cost. Requires funding and must finish before private beta. |
| **M7 — Credits and immutable billing ledger** | Append-only ledger, atomic reservations/settlements/refunds, concurrency safety, idempotency, auditability, and reconciliation. |
| **M8 — Paystack and Nigerian payment architecture** | Payment initiation, signed and idempotent webhooks, server verification, atomic credit allocation, and reconciliation. Local/mock payment paths remain available. |
| **M9 — Guided AI Ad Builder** | Guided questions, normalized specification creation, prompt preview/editing, and the shared generation path. |
| **M10 — Finishing pipeline** | Selective captions, voiceover, supported audio/music, thumbnails, aspect-ratio variants, scene regeneration, and export. Capabilities stay local or mocked where zero-spend requires it. |
| **M11 — Private beta** | Limited-user validation, support and operational feedback. Blocked until M6R succeeds. |
| **M12 — Production and launch readiness** | Security and reliability review, observability, backups/recovery, capacity validation, incident procedures, privacy readiness, and release controls. |

Milestone gates should include tests for the newly introduced risks, migration and rollback review where applicable, documentation updates, and confirmation that local development remains independent of paid services.
