# Adsyde

Adsyde is a Nigeria-first advertising product for businesses and creators who need polished video advertisements. It will provide a guided creation flow for people who do not write prompts and a Prompt Studio for people who want direct control.

Milestone 1 establishes the backend engineering foundation. No product workflow, generation provider, authentication API, billing, frontend, or deployment has been implemented.

## Product principles

- Adsyde owns the customer workflow and business rules; generation providers remain replaceable infrastructure.
- Guided and prompt-based creation converge on one normalized ad specification.
- A custom prompt is never silently rewritten. Prompt enhancement is explicit and optional.
- Security, database integrity, idempotency, and auditability are design requirements.
- Local development and automated tests must work without paid services or live financial transactions.

## Planned repository layout

```text
adsyde/
├── backend/     # Django API foundation
├── frontend/    # Next.js application, introduced when needed
├── docs/        # Product, architecture, roadmap, and engineering policy
├── .gitignore
└── README.md
```

The frontend and later service components will be added by their implementation milestones rather than maintained as empty placeholders.

## Documentation

- [Product and architecture](docs/architecture.md)
- [Milestone roadmap](docs/roadmap.md)
- [Engineering and security rules](docs/engineering-security.md)
- [Backend development](backend/README.md)

## Current scope

Milestone 1 implements infrastructure only. See the roadmap for later scope. Real provider validation is deliberately deferred until funding is available and must succeed before private beta.
