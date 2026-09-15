from django.db import models

from apps.accounts.users.models import User
from apps.core.base.models import BaseModel


class NotificationType(models.TextChoices):
    NEW_MATCH = "new_match", "Yangi moslik"
    NEW_MESSAGE = "new_message", "Yangi xabar"
    PROFILE_VIEWED = "profile_viewed", "Profil ko'rildi"
    SYSTEM = "system", "Tizim xabari"


class Notification(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="notifications",
        verbose_name="Foydalanuvchi",
    )
    type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        verbose_name="Turi",
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


class NotificationPreference(BaseModel):
    """Foydalanuvchining bildirishnoma turlari bo'yicha yoqilgan/o'chirilgan sozlamalari."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="notification_preference",
        verbose_name="Foydalanuvchi",
    )
    new_match = models.BooleanField(default=True, verbose_name="Yangi moslik")
    new_message = models.BooleanField(default=True, verbose_name="Yangi xabar")
    profile_viewed = models.BooleanField(default=True, verbose_name="Profil ko'rildi")
    system_messages = models.BooleanField(default=True, verbose_name="Tizim xabarlari")

    class Meta:
        verbose_name = "Bildirishnoma sozlamasi"
        verbose_name_plural = "Bildirishnoma sozlamalari"

    def __str__(self):
        return f"{self.user} - bildirishnoma sozlamalari"


NOTIFICATION_TYPE_PREFERENCE_FIELDS = {
    NotificationType.NEW_MATCH: "new_match",
    NotificationType.NEW_MESSAGE: "new_message",
    NotificationType.PROFILE_VIEWED: "profile_viewed",
    NotificationType.SYSTEM: "system_messages",
}


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
