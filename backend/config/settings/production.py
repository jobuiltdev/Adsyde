import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import LOCAL_DATABASE_URL, LOCAL_SECRET_KEY
from .environment import env_bool, env_list, require_production

EMAIL_BACKEND = require_production("EMAIL_BACKEND")
FRONTEND_BASE_URL = require_production(
    "FRONTEND_BASE_URL", lambda value: value.startswith("https://")
).rstrip("/")

SECRET_KEY = require_production(
    "SECRET_KEY", lambda value: value != LOCAL_SECRET_KEY and len(value) >= 32
)
DATABASE_URL = require_production("DATABASE_URL", lambda value: value != LOCAL_DATABASE_URL)
if not DATABASE_URL.startswith(("postgresql://", "postgres://")):
    raise ImproperlyConfigured("DATABASE_URL must use PostgreSQL in production")
DEBUG = False
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be set in production")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
if env_bool("TRUST_PROXY_SSL_HEADER", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
