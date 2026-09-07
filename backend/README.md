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
