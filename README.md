# Adsyde

Adsyde is a Nigeria-first advertising product for businesses and creators who need polished video advertisements. It will provide a guided creation flow for people who do not write prompts and a Prompt Studio for people who want direct control.

The current product includes the Django API, asynchronous local generation engine, and a Next.js creative workspace. Local development remains zero-spend and uses the deterministic mock provider.

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

The frontend is a separate Next.js application and proxies browser API requests to Django during local development.

## Documentation

- [Product and architecture](docs/architecture.md)
- [Milestone roadmap](docs/roadmap.md)
- [Engineering and security rules](docs/engineering-security.md)
- [Backend development](backend/README.md)
- [Frontend development](frontend/README.md)
- [Provider integration readiness](docs/provider-readiness.md)

## Current scope

Run the backend stack from `backend/`, then run the Next.js application from `frontend/`. Real provider validation remains deliberately deferred until funding is available and must succeed before private beta.
