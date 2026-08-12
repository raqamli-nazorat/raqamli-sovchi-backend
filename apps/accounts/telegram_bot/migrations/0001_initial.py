import uuid
import apps.accounts.telegram_bot.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def default_expires_at():
    from django.utils import timezone
    return timezone.now() + timezone.timedelta(minutes=5)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TelegramAuthSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("session_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True, verbose_name="Sessiya ID")),
                ("status", models.CharField(
                    choices=[("pending", "Kutilmoqda"), ("authenticated", "Tasdiqlangan"), ("expired", "Muddati o'tgan")],
                    default="pending", max_length=20, verbose_name="Holat"
                )),
                ("user", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="telegram_sessions",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Foydalanuvchi",
                )),
                ("access_token", models.TextField(blank=True, null=True, verbose_name="Access Token")),
                ("refresh_token", models.TextField(blank=True, null=True, verbose_name="Refresh Token")),
                ("expires_at", models.DateTimeField(default=apps.accounts.telegram_bot.models.default_expires_at, verbose_name="Amal qilish muddati")),
            ],
            options={
                "verbose_name": "Telegram Auth Sessiyasi",
                "verbose_name_plural": "Telegram Auth Sessiyalari",
                "db_table": "telegram_auth_sessions",
                "ordering": ["-created_at"],
            },
        ),
    ]
