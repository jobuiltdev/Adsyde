# Backend

The backend uses Python 3.13, Django 5.2 LTS, Django REST Framework, Psycopg 3, and PostgreSQL. Product APIs will use `/api/v1/`; the unversioned `/api/health/` and `/api/readiness/` endpoints are operational contracts.

## Local setup

Create and activate a Python 3.13 virtual environment, then install the project:

```shell
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env`, replace its local-only secret placeholder, and load those values through your shell or environment manager. Django does not read secret files automatically. Set `DATABASE_URL` to a PostgreSQL database using `postgresql://USER:PASSWORD@HOST:PORT/DATABASE`.

```shell
python manage.py migrate
python manage.py runserver
pytest
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
```

Docker is optional. `docker compose up --build` starts PostgreSQL on the private Compose network and exposes the development server on port `8000`. It provisions no remote infrastructure. One-off checks use `docker compose run --rm web <command>`.

## Architecture choices

- `config.settings.base` contains shared defaults; `local`, `test`, and `production` specialize them.
- Production requires a strong `SECRET_KEY`, PostgreSQL `DATABASE_URL`, and explicit `ALLOWED_HOSTS`. It enables secure cookies and HTTPS controls. Tests retain PostgreSQL and never silently use SQLite.
- DRF denies access by default and authenticates product APIs with JWT bearer access tokens. Public authentication and operational views explicitly use `AllowAny`.
- Scoped throttling supports endpoint-specific policy. Operational rates are configurable and deliberately generous; future production account and product values remain deferred.
- CORS is deferred until the frontend origin and credential strategy exist. CSRF middleware remains enabled.
- Logs are JSON on stdout/stderr. A bounded supplied or generated request ID is included in logs and responses. API errors use a stable envelope.
- Accounts use UUID identifiers and case-insensitive normalized email identity. A nullable verification timestamp records when email ownership was established.

## Authentication and accounts

Product authentication is available under `/api/v1/`:

- `POST auth/register/` creates an unverified account and queues a verification email.
- `POST auth/verify-email/` consumes a single-use, expiring verification link.
- `POST auth/verification/resend/` returns the same response for known and unknown emails.
- `POST auth/login/` issues access and refresh tokens only for active, verified accounts.
- `POST auth/refresh/` rotates the refresh token and blacklists the previous token.
- `POST auth/logout/` revokes the submitted refresh token and is safely repeatable.
- `POST auth/password-reset/` returns a generic response and conditionally sends reset mail.
- `POST auth/password-reset/confirm/` changes the password and revokes all refresh tokens.
- `GET me/` returns the current account's public fields.
- `PATCH me/` changes the password after checking the current password and revokes all refresh tokens.

Access tokens last 15 minutes and refresh tokens last 7 days by default. Both lifetimes are configurable. Already-issued access tokens remain valid until their short expiry after logout or a password change; refresh tokens are server-revocable and are recorded only as token metadata by SimpleJWT's blacklist application. Direct email changes are deferred because they require a pending-email and re-verification workflow.

Password reset and authenticated password change blacklist all outstanding refresh tokens inside the password-update transaction. Deactivated accounts are rejected by JWT authentication and refresh validation even if token records remain; a future account-deactivation workflow should also blacklist those records for explicit cleanup.

The API does not prescribe browser token storage. The frontend credential transport, XSS exposure, and any cookie/CSRF design must be decided together; CSRF middleware remains enabled.

Local email uses Django's console backend and tests use the in-memory backend, so no network email is sent. Production requires an explicit email backend and HTTPS `FRONTEND_BASE_URL`; provider selection is deferred. Verification and reset URLs are built from `FRONTEND_BASE_URL`. Configure `DEFAULT_FROM_EMAIL`, `EMAIL_VERIFICATION_TIMEOUT_SECONDS`, and `PASSWORD_RESET_TIMEOUT_SECONDS` as needed.

Authentication endpoints use distinct configurable throttle scopes: registration, login, verification submission, verification resend, refresh, reset request, reset confirmation, logout, and account update. Defaults are conservative local starting values, not settled production policy. Deployed counters should move to a shared cache after Redis is introduced in a later milestone. Adaptive account/IP login protection is also deferred; permanent account lockouts are intentionally not used.

## Projects and assets

Authenticated project APIs are available at `/api/v1/projects/` and `/api/v1/projects/{id}/`. Projects contain a name plus optional business name, description, brand style, and target audience. Ownership is always assigned from the authenticated request and every query is owner-scoped; probing another account's identifiers returns the same `404` behavior as a missing resource. Lists are paginated and newest-first.

Assets use these project-scoped routes:

- `GET|POST /api/v1/projects/{project_id}/assets/`
- `GET|DELETE /api/v1/projects/{project_id}/assets/{asset_id}/`
- `GET /api/v1/projects/{project_id}/assets/{asset_id}/content/`

Uploads accept multipart JPEG, PNG, and WebP images in the `product_image`, `logo`, or `reference_image` category. SVG, GIF, malformed files, and other formats are rejected. Pillow decodes and verifies the actual content; request MIME and filename extensions are not authoritative. The canonical MIME, dimensions, and byte size are persisted. Default limits are 10 MiB per file, 8,192 pixels per dimension, 40 million total pixels, and 30 assets per project. A separate 11 MiB request-body limit rejects oversized requests from their declared content length before parsing, while Django's upload-memory threshold controls when files spill to temporary storage. Deployment proxies must enforce the same request limit, including for clients that omit content length. These limits and the project-create, project-mutation, asset-upload, asset-delete, and asset-access throttle rates are configurable through the environment variables in `.env.example`.

Storage uses Django's storage interface. Local files are placed under `MEDIA_ROOT` with server-generated `projects/<project UUID>/assets/<asset UUID>.<canonical extension>` keys. APIs never return storage paths; content is served only after JWT authentication and an ownership lookup. A later S3-compatible backend can replace local storage through configuration and use temporary delivery URLs without changing asset records or ownership rules.

Project deletion is deliberately hard-delete while no generation or financial history depends on projects. Cascading asset records schedule physical deletion with `transaction.on_commit()`, as does direct asset deletion, so rollback cannot leave a retained database record pointing to a deliberately removed file. Upload validation happens before storage. Quota checking and record creation lock the project row; if database creation fails after file storage, the file is explicitly removed.

Validated original image bytes are preserved in M3. EXIF and other embedded metadata are therefore not claimed to be stripped; raster normalization and privacy-oriented metadata removal are required before production. This avoids silent quality or transparency changes until a tested normalization policy is introduced.

## Generation engine

Generation APIs are project-scoped and authenticated:

- `GET|POST /api/v1/projects/{project_id}/generations/`
- `GET /api/v1/projects/{project_id}/generations/{generation_id}/`
- `POST /api/v1/projects/{project_id}/generations/{generation_id}/cancel/`
- `GET /api/v1/projects/{project_id}/generations/{generation_id}/result/`

Submission accepts a prompt, `9:16`, `1:1`, or `16:9` aspect ratio, a configurable 5–20 second duration, and `mock-standard` or `mock-premium`. Prompts default to a 4,000-character maximum. Ownership is inherited through the project, and a locked user row protects the default five-active-generation cap. The API commits a `queued` record before enqueueing work with `transaction.on_commit()`.

The lifecycle is `draft → queued → submitted → processing → completed`, with explicit failure and cancellation transitions. `submitted` or `processing` work can enter `unknown` when provider acceptance or state is uncertain; bounded reconciliation can then return it to processing or resolve it to completed/failed. Completed, failed, and cancelled states never regress. Every transition is centralized behind row-locked services.

The provider package defines typed request/status objects, a neutral provider contract, error taxonomy, and registry. M4 registers only the deterministic `mock` provider. It simulates success, slow processing, rejection, provider failure, transient and persistent unavailability, timeout before acceptance, timeout after possible acceptance, malformed responses, reconciliation success/failure, and cancellation. Stable idempotency keys produce stable mock job IDs. Real providers and credentials remain deferred to M6R.

Celery uses JSON serialization, late acknowledgement, rejection on worker loss, bounded exponential submission retries, and Redis as its local broker. Polling uses configurable countdown tasks rather than a busy loop or Celery Beat. Important provider identifiers are persisted before follow-up work is queued, allowing polling/reconciliation to resume after a worker crash. Duplicate tasks short-circuit from persisted state. Provider event receipts have a unique provider/event identifier; duplicate and late events are retained harmlessly without overwriting terminal state.

Successful mock work writes a tiny runtime MP4 container marker through Django storage. It is explicitly mock infrastructure, not an AI-generated or playable advertisement. Result content is available only through the ownership-checked endpoint; storage paths are never serialized. Runtime media remains ignored by Git and future object storage can replace the backend.

Local Compose includes PostgreSQL, Redis, the API, and a Celery worker. Run `docker compose up --build` for the complete stack. Tests execute tasks eagerly and deterministically; no network provider is contacted. Generation submit, cancel, and status scopes default to `20/hour`, `30/hour`, and `240/hour` per authenticated user. Production retry timing, provider-specific webhook signatures, real media validation, and providers without native idempotency require explicit design during real-provider validation.
