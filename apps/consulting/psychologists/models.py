from django.db import models

from apps.core.base.models import BaseModel
from apps.core.utils.validators import phone_validator


class Psychologist(BaseModel):
    """Platformadagi psixolog-mutaxassis. Boshqaruv paneli orqali boshqariladi."""

    first_name = models.CharField(max_length=100, verbose_name="Ismi")
    last_name = models.CharField(max_length=100, verbose_name="Familiyasi")
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[phone_validator],
        verbose_name="Telefon raqam",
    )
    specialization = models.CharField(max_length=255, verbose_name="Mutaxassislik")
    experience_years = models.PositiveSmallIntegerField(verbose_name="Tajriba (yil)")
    price = models.PositiveIntegerField(verbose_name="Sessiya narxi (so'm)")
    session_duration_minutes = models.PositiveSmallIntegerField(
        verbose_name="Sessiya davomiyligi (daqiqa)"
    )
    bio = models.TextField(blank=True, verbose_name="Tavsif")
    photo = models.ImageField(
        upload_to="psychologists/", null=True, blank=True, verbose_name="Rasm"
    )
    is_available = models.BooleanField(
        default=True, db_index=True, verbose_name="Qabul qilmoqda"
    )

    class Meta:
        verbose_name = "Psixolog"
        verbose_name_plural = "Psixologlar"
        db_table = "psychologists"

    def __str__(self):
        return f"{self.full_name} — {self.specialization}"

    @property
    def full_name(self):
        """To'liq ism: ism va familiyaning birlashmasi."""
        return f"{self.first_name} {self.last_name}".strip()
