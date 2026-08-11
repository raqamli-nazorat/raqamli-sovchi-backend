from django.contrib import admin
from apps.core.base.admin import BaseModelAdmin
from .models import (
    EducationLevel,
    Nationality,
    Profession,
    MaritalStatus,
    HealthStatus,
    Kinship,
)


@admin.register(EducationLevel)
class EducationLevelAdmin(BaseModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(Nationality)
class NationalityAdmin(BaseModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(Profession)
class ProfessionAdmin(BaseModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(MaritalStatus)
class MaritalStatusAdmin(BaseModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(HealthStatus)
class HealthStatusAdmin(BaseModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(Kinship)
class KinshipAdmin(BaseModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)
