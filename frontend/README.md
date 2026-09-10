# Adsyde frontend

Next.js App Router application for Adsyde's authenticated creative workspace and Prompt Studio.

## Local setup

1. Start PostgreSQL, Redis, Django, and Celery from `backend/` with `docker compose up --build`.
2. Copy `.env.example` to `.env.local` if Django is not at `http://localhost:8000`.
3. Run `npm install` and `npm run dev` from this directory.
4. Open `http://localhost:3000`.

The Next.js server proxies `/backend/*` through a route handler to Django. This keeps browser API traffic same-origin without weakening Django's CSRF or cross-origin policy and preserves Django's trailing-slash API contract.

## Authentication security

The M2 API returns JWTs in JSON rather than secure cookies. The access token is held only in memory. The rotating refresh token is kept in tab-scoped `sessionStorage`, cleared on logout or failed refresh, and never placed in URLs or logs. This is safer than durable `localStorage`, but JavaScript-visible refresh tokens remain exposed if an XSS vulnerability occurs. Moving refresh transport to an HttpOnly, Secure, SameSite cookie is deferred to a deliberately scoped backend change.

Private images and video are requested with the access token, converted to object URLs, and revoked when their component unmounts or content changes. No filesystem or public media URLs are used.

## Checks

Run `npm run lint`, `npm run typecheck`, `npm test`, and `npm run build`.
