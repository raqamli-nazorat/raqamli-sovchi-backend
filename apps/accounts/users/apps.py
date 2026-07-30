from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts.users"
    verbose_name = "Foydalanuvchilar"

    def ready(self):
        import apps.accounts.users.signals  # noqa
