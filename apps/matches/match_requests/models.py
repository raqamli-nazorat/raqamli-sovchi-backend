from django.db import models

from apps.accounts.profiles.models import Profile
from apps.accounts.questionnaire.models import Question
from apps.core.base.models import BaseModel


class MatchRequestStatus(models.TextChoices):
    PENDING = "pending", "Kutilmoqda"
    ACCEPTED = "accepted", "Qabul qilindi"
    REJECTED = "rejected", "Rad etildi"


class MatchRequest(BaseModel):
    from_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="sent_match_requests",
        verbose_name="Yuboruvchi profil",
    )
    to_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="received_match_requests",
        verbose_name="Qabul qiluvchi profil",
    )
    status = models.CharField(
        max_length=20,
        choices=MatchRequestStatus.choices,
        default=MatchRequestStatus.PENDING,
        verbose_name="Holati",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="match_requests",
        verbose_name="Savol",
    )

    class Meta:
        verbose_name = "Moslik so'rovi"
        verbose_name_plural = "Moslik so'rovlari"
        db_table = "match_requests"

    def __str__(self):
        return f"{self.from_profile} -> {self.to_profile} ({self.get_status_display()})"
