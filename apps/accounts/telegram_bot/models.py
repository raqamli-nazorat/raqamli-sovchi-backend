import uuid
from django.utils import timezone
from django.db import models
from apps.core.base.models import BaseModel
from apps.accounts.users.models import User


def generate_code():
    return ""


def default_expires_at():
    return timezone.now() + timezone.timedelta(minutes=5)


class SessionStatus(models.TextChoices):
    PENDING = "pending", "Kutilmoqda"
    AUTHENTICATED = "authenticated", "Tasdiqlangan"
    EXPIRED = "expired", "Muddati o'tgan"


class TelegramAuthSession(BaseModel):
    session_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name="Sessiya ID",
    )
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.PENDING,
        verbose_name="Holat",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_sessions",
        verbose_name="Foydalanuvchi",
    )
    access_token = models.TextField(blank=True, null=True, verbose_name="Access Token")
    refresh_token = models.TextField(
        blank=True, null=True, verbose_name="Refresh Token"
    )
    expires_at = models.DateTimeField(
        default=default_expires_at,
        verbose_name="Amal qilish muddati",
    )

    class Meta:
        verbose_name = "Telegram Auth Sessiyasi"
        verbose_name_plural = "Telegram Auth Sessiyalari"
        db_table = "telegram_auth_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.session_id} — {self.get_status_display()}"

    def is_valid(self):
        return self.status == SessionStatus.PENDING and timezone.now() < self.expires_at
