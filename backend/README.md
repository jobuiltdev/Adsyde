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
- DRF denies access by default and has no authentication mechanism until M2. Public operational views explicitly use `AllowAny`.
- Scoped throttling supports endpoint-specific policy. Operational rates are configurable and deliberately generous; future production account and product values remain deferred.
- CORS is deferred until the frontend origin and credential strategy exist. CSRF middleware remains enabled.
- Logs are JSON on stdout/stderr. A bounded supplied or generated request ID is included in logs and responses. API errors use a stable envelope.
- The minimal user model uses UUID identifiers and case-insensitive unique, normalized email identity. Authentication APIs and profile data remain M2 scope.
