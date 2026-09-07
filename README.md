# Adsyde

Adsyde is a Nigeria-first advertising product for businesses and creators who need polished video advertisements. It will provide a guided creation flow for people who do not write prompts and a Prompt Studio for people who want direct control.

The product is in Milestone 0: product and engineering foundation. No application, generation provider, authentication, billing, or deployment has been implemented.

## Product principles

- Adsyde owns the customer workflow and business rules; generation providers remain replaceable infrastructure.
- Guided and prompt-based creation converge on one normalized ad specification.
- A custom prompt is never silently rewritten. Prompt enhancement is explicit and optional.
- Security, database integrity, idempotency, and auditability are design requirements.
- Local development and automated tests must work without paid services or live financial transactions.

## Planned repository layout

```text
adsyde/
├── backend/     # Django and worker services, introduced in M1
├── frontend/    # Next.js application, introduced when needed
├── docs/        # Product, architecture, roadmap, and engineering policy
├── .gitignore
└── README.md
```

Framework directories will be added by their implementation milestones rather than maintained as empty placeholders.

## Documentation

- [Product and architecture](docs/architecture.md)
- [Milestone roadmap](docs/roadmap.md)
- [Engineering and security rules](docs/engineering-security.md)

## Current scope

Milestone 0 defines boundaries and implementation expectations only. See the roadmap for later scope. Real provider validation is deliberately deferred until funding is available and must succeed before private beta.
