from django.db import models
from apps.core.base.models import BaseModel


class EducationLevel(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Nomi")

    class Meta:
        verbose_name = "Ta'lim darajasi"
        verbose_name_plural = "Ta'lim darajalari"
        db_table = "education_levels"

    def __str__(self):
        return self.name


class Nationality(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Nomi")

    class Meta:
        verbose_name = "Millat"
        verbose_name_plural = "Millatlar"
        db_table = "nationalities"

    def __str__(self):
        return self.name


class Profession(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Nomi")

    class Meta:
        verbose_name = "Kasb"
        verbose_name_plural = "Kasblar"
        db_table = "professions"


class MaritalStatus(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Nomi")

    class Meta:
        verbose_name = "Oilaviy holati"
        verbose_name_plural = "Oilaviy holatlari"
        db_table = "marital_statuses"

    def __str__(self):
        return self.name


class HealthStatus(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Nomi")

    class Meta:
        verbose_name = "Sog'liq holati"
        verbose_name_plural = "Sog'liq holatlari"
        db_table = "health_statuses"

    def __str__(self):
        return self.name


class Kinship(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Nomi")

    class Meta:
        verbose_name = "Qarindoshlik holati"
        verbose_name_plural = "Qarindoshlik holatlari"
        db_table = "kinships"

    def __str__(self):
        return self.name
