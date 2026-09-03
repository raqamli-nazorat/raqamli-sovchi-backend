from django.conf import settings
from django.db import models

from apps.core.base.models import BaseModel


class ComplaintReason(models.TextChoices):
    ABUSIVE_LANGUAGE = "abusive_language", "Odobsiz so'z"
    FAKE_PROFILE = "fake_profile", "Soxta profil"
    FRAUD = "fraud", "Firibgarlik"
    SPAM = "spam", "Spam va reklama"
    FALSE_INFORMATION = "false_information", "Noto'g'ri ma'lumot"
    THREAT = "threat", "Haqorat va tahdid"
    NO_SERIOUS_INTENT = "no_serious_intent", "Nikoh niyati yo'q"
    OTHER = "other", "Boshqa"


class ComplaintStatus(models.TextChoices):
    PENDING = "pending", "Ko'rib chiqilmoqda"
    APPROVED = "approved", "Tasdiqlandi"
    REJECTED = "rejected", "Bekor qilindi"


class Complaint(BaseModel):
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_complaints",
        verbose_name="Shikoyat yuboruvchi",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_complaints",
        verbose_name="Shikoyat qilingan foydalanuvchi",
    )
    chat_room = models.ForeignKey(
        "chats.ChatRoom",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
        verbose_name="Chat xonasi",
    )
    reason = models.CharField(
        max_length=50,
        choices=ComplaintReason.choices,
        verbose_name="Shikoyat sababi",
    )
    message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Qo'shimcha izoh",
    )
    evidence = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Dalillar",
    )
    status = models.CharField(
        max_length=20,
        choices=ComplaintStatus.choices,
        default=ComplaintStatus.PENDING,
        verbose_name="Holati",
    )
    admin_note = models.TextField(
        blank=True,
        null=True,
        verbose_name="Admin izohi",
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_complaints",
        verbose_name="Ko'rib chiqqan admin",
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ko'rib chiqilgan vaqt",
    )

    class Meta:
        verbose_name = "Shikoyat"
        verbose_name_plural = "Shikoyatlar"
        db_table = "complaints"

    def __str__(self):
        """Shikoyatning qisqa matn ko'rinishini qaytaradi."""
        return (
            f"{self.from_user_id} -> {self.to_user_id}"
            f" ({self.get_reason_display()})"
        )

