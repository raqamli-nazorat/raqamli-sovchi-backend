from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts.notifications"

    def ready(self):
        import apps.accounts.notifications.signals  # noqa: F401
