# Guided Ad Builder

The Guided Ad Builder turns a small set of campaign inputs into an editable ad plan without making an external AI or provider call. Prompt Studio remains an equal creation path and accepts a guided plan handoff without hidden rewriting.

## Domain and lifecycle

`AdPlan` stores the project-owned draft inputs and generation settings. A draft is saved when the user advances through the builder, which provides authenticated backend persistence without saving on every keystroke. Selected project assets are stored as ordered `AdPlanAsset` records with an explicit role: primary product, additional product, logo, or visual reference.

Planning creates an immutable-source `AdPlanRevision`. Each revision retains the planner concept, hook, structured script, structured shot plan, and prompt alongside separate reviewed fields. User edits change only the reviewed fields. An idempotency key prevents retry or double-click requests from creating duplicate revisions; an explicit regeneration uses a new key and creates a new version.

The plan lifecycle is `draft`, `planned`, `generated`, or `archived`. Ungenerated plans can be deleted. Deleting a generated plan archives it, and a project with generated plan history cannot be deleted through the API. This protects generation and billing provenance.

## Planner abstraction

`AdPlanner` accepts a provider-independent `PlannerRequest` and returns a structured `PlannerResult`. M9 supplies only `DeterministicPlanner` (`deterministic-v1` with `prompt-template-v1`). It uses stable revision variants, platform pacing rules, input-preserving copy, and exact integer-millisecond shot allocation. It does not invent stronger product claims and it makes no network calls.

A future planner can implement the same interface:

```text
PlannerRequest -> LLMPlanner -> validated PlannerResult -> existing revision/UI flow
```

No LLM vendor integration or planning charge exists in M9. Production moderation remains required before public launch.

## Inputs and safety

The required product/business description is joined by an optional offer or objective, audience, curated style plus notes, platform, CTA, up to eight selling points, generation model, supported ratio and duration, and up to eight ordered assets. Project brand fields prefill useful context but remain overridable per ad.

Model, ratio, and duration are validated against the active generation provider catalogue. A lightweight deterministic boundary rejects clearly harmful, illegal-product, weapon-building, and real-person impersonation/deepfake instructions. It is intentionally not a complete regulated-ad policy or production moderation system.

## Asset and prompt provenance

Plan assets snapshot ID, filename, category, MIME type, role, and position. Asset deletion sets the live relation to null while retaining this context. Direct generation copies those snapshots to `GenerationReference`, so historical semantics survive later asset deletion without exposing public media URLs.

The original planner prompt and editable reviewed prompt remain separate. Direct generation submits the exact reviewed prompt with no hidden enhancement and links the resulting generation one-to-one to its source revision. Credit pricing and reservation use the existing authoritative generation flow; planning and editing are free. A short balance blocks only final generation.

“Open in Prompt Studio” passes the project, exact reviewed prompt, supported model, duration, ratio, and selected asset IDs through same-browser session storage. Prompt Studio then owns its copy and does not synchronize later edits back to the guided revision.

## M10 boundary

Captions, voice synthesis, licensed music, thumbnails, scene regeneration, duplication, finishing behavior, download polish, and trial watermark behavior remain deferred to M10.
