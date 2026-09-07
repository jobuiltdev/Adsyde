from django.conf import settings


def test_safe_baseline_settings():
    assert settings.USE_TZ is True
    assert settings.TIME_ZONE == "UTC"
    assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert settings.X_FRAME_OPTIONS == "DENY"
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated"
    ]
    assert settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == []
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
