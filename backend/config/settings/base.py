from datetime import timedelta
from pathlib import Path

import dj_database_url

from .environment import env, env_bool, env_list

BASE_DIR = Path(__file__).resolve().parents[2]
LOCAL_SECRET_KEY = "local-development-only-not-for-shared-environments"
LOCAL_DATABASE_URL = "postgresql://adsyde:adsyde@localhost:5432/adsyde"

SECRET_KEY = env("SECRET_KEY", LOCAL_SECRET_KEY)
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "apps.accounts",
    "apps.projects",
    "apps.assets",
    "apps.generations",
    "apps.providers",
    "apps.core",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.RequestIDMiddleware",
    "apps.core.middleware.RequestSizeLimitMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL", LOCAL_DATABASE_URL), conn_max_age=60, conn_health_checks=True
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
AUTH_USER_MODEL = "accounts.User"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
FILE_UPLOAD_MAX_MEMORY_SIZE = int(env("FILE_UPLOAD_MAX_MEMORY_SIZE", "2621440"))
DATA_UPLOAD_MAX_MEMORY_SIZE = int(env("DATA_UPLOAD_MAX_MEMORY_SIZE", "11534336"))
REQUEST_MAX_BODY_SIZE = int(env("REQUEST_MAX_BODY_SIZE", "11534336"))
ASSET_MAX_FILE_SIZE = int(env("ASSET_MAX_FILE_SIZE", "10485760"))
ASSET_MAX_DIMENSION = int(env("ASSET_MAX_DIMENSION", "8192"))
ASSET_MAX_PIXELS = int(env("ASSET_MAX_PIXELS", "40000000"))
ASSET_MAX_PER_PROJECT = int(env("ASSET_MAX_PER_PROJECT", "30"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "health": env("THROTTLE_HEALTH_RATE", "120/min"),
        "readiness": env("THROTTLE_READINESS_RATE", "60/min"),
        "test": env("THROTTLE_TEST_RATE", "2/min"),
        "auth_register": env("THROTTLE_AUTH_REGISTER_RATE", "5/min"),
        "auth_login": env("THROTTLE_AUTH_LOGIN_RATE", "5/min"),
        "auth_verify": env("THROTTLE_AUTH_VERIFY_RATE", "10/hour"),
        "auth_verification_resend": env("THROTTLE_AUTH_VERIFICATION_RESEND_RATE", "3/hour"),
        "auth_refresh": env("THROTTLE_AUTH_REFRESH_RATE", "20/min"),
        "auth_password_reset": env("THROTTLE_AUTH_PASSWORD_RESET_RATE", "5/hour"),
        "auth_password_reset_confirm": env("THROTTLE_AUTH_PASSWORD_RESET_CONFIRM_RATE", "10/hour"),
        "auth_logout": env("THROTTLE_AUTH_LOGOUT_RATE", "20/hour"),
        "account_update": env("THROTTLE_ACCOUNT_UPDATE_RATE", "20/hour"),
        "project_create": env("THROTTLE_PROJECT_CREATE_RATE", "20/hour"),
        "project_mutation": env("THROTTLE_PROJECT_MUTATION_RATE", "60/hour"),
        "asset_upload": env("THROTTLE_ASSET_UPLOAD_RATE", "30/hour"),
        "asset_delete": env("THROTTLE_ASSET_DELETE_RATE", "60/hour"),
        "asset_access": env("THROTTLE_ASSET_ACCESS_RATE", "120/hour"),
        "generation_submit": env("THROTTLE_GENERATION_SUBMIT_RATE", "20/hour"),
        "generation_cancel": env("THROTTLE_GENERATION_CANCEL_RATE", "30/hour"),
        "generation_status": env("THROTTLE_GENERATION_STATUS_RATE", "240/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("JWT_ACCESS_LIFETIME_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("JWT_REFRESH_LIFETIME_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Adsyde <no-reply@localhost>")
FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
EMAIL_VERIFICATION_TIMEOUT = int(env("EMAIL_VERIFICATION_TIMEOUT_SECONDS", "86400"))
PASSWORD_RESET_TIMEOUT = int(env("PASSWORD_RESET_TIMEOUT_SECONDS", "3600"))

CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = None
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
GENERATION_MAX_ACTIVE_PER_USER = int(env("GENERATION_MAX_ACTIVE_PER_USER", "5"))
GENERATION_MAX_PROMPT_LENGTH = int(env("GENERATION_MAX_PROMPT_LENGTH", "4000"))
GENERATION_MIN_DURATION_SECONDS = int(env("GENERATION_MIN_DURATION_SECONDS", "5"))
GENERATION_MAX_DURATION_SECONDS = int(env("GENERATION_MAX_DURATION_SECONDS", "20"))
GENERATION_POLL_INTERVAL_SECONDS = int(env("GENERATION_POLL_INTERVAL_SECONDS", "5"))
GENERATION_MAX_TASK_ATTEMPTS = int(env("GENERATION_MAX_TASK_ATTEMPTS", "3"))
GENERATION_MAX_RECONCILIATION_ATTEMPTS = int(env("GENERATION_MAX_RECONCILIATION_ATTEMPTS", "5"))

LOG_LEVEL = env("LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "apps.core.logging.RequestIDFilter"}},
    "formatters": {"json": {"()": "apps.core.logging.JSONFormatter"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_id"],
            "formatter": "json",
        }
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.server": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django.db.backends": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
