from django.apps import AppConfig


class TelegramIntegrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.telegram_integration"
    verbose_name = "Telegram Integration"

    def ready(self):
        from . import signals  # noqa: F401
