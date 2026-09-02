from django.db import models

from apps.accounts.users.models import User
from apps.core.base.models import BaseModel


class Notification(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="notifications",
        verbose_name="Foydalanuvchi",
    )
    title = models.CharField(max_length=255, default="", verbose_name="Sarlavha")
    message = models.TextField(default="", verbose_name="Xabar matni")
    extra_data = models.JSONField(
        null=True, blank=True, verbose_name="Qo'shimcha ma'lumot"
    )
    is_read = models.BooleanField(default=False, verbose_name="O'qilganmi?")

    class Meta:
        verbose_name = "Xabarnoma"
        verbose_name_plural = "Xabarnomalar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.title}"


class UserDevice(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="notification_devices"
    )
    fcm_token = models.TextField(unique=True)
    device_type = models.CharField(
        max_length=50, choices=[("ios", "iOS"), ("android", "Android"), ("web", "Web")]
    )
    device_id = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.user} - {self.device_type}"
