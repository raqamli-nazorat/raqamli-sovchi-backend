from django.db import models
from apps.core.base.models import BaseModel


class Region(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Nomi")
    code = models.PositiveIntegerField(null=True, blank=True, verbose_name="Kodi")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Viloyat"
        verbose_name_plural = "Viloyatlar"


class District(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Nomi")
    code = models.PositiveIntegerField(null=True, blank=True, verbose_name="Kodi")
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="districts",
        verbose_name="Viloyati",
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Tuman"
        verbose_name_plural = "Tumanlar"
