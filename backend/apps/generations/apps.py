from django.apps import AppConfig


class GenerationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.generations"

    def ready(self):
        from . import signals  # noqa: F401
