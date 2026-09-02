from django.db import models

from apps.accounts.profiles.models import Profile
from apps.core.base.models import BaseModel


class PhotoRequestStatus(models.TextChoices):
    PENDING = "pending", "Kutilmoqda"
    ACCEPTED = "accepted", "Qabul qilindi"
    REJECTED = "rejected", "Rad etildi"


class PhotoRequest(BaseModel):
    from_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="sent_photo_requests",
        verbose_name="Yuboruvchi profil",
    )
    to_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="received_photo_requests",
        verbose_name="Qabul qiluvchi profil",
    )
    status = models.CharField(
        max_length=20,
        choices=PhotoRequestStatus.choices,
        default=PhotoRequestStatus.PENDING,
        verbose_name="Holati",
    )
    note = models.TextField(
        blank=True,
        null=True,
        verbose_name="Izoh",
    )

    class Meta:
        verbose_name = "Rasm ko'rish so'rovi"
        verbose_name_plural = "Rasm ko'rish so'rovlari"
        db_table = "photo_requests"

    def __str__(self):
        return f"{self.from_profile} -> {self.to_profile} ({self.get_status_display()})"
