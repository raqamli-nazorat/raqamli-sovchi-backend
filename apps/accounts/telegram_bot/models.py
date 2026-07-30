import random
from django.utils import timezone
from django.db import models
from apps.core.base.models import BaseModel


def generate_code():
    return str(random.randint(100000, 999999))


def default_expires_at():
    return timezone.now() + timezone.timedelta(minutes=5)


class LoginCode(BaseModel):
    phone_number = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name="Telefon raqam",
    )
    code = models.CharField(
        max_length=6,
        default=generate_code,
        verbose_name="Tasdiqlash kodi",
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="Ishlatilgan",
    )
    expires_at = models.DateTimeField(
        default=default_expires_at,
        verbose_name="Amal qilish muddati",
    )

    class Meta:
        verbose_name = "Login kodi"
        verbose_name_plural = "Login kodlari"
        db_table = "telegram_login_codes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.phone_number} — {self.code}"

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
