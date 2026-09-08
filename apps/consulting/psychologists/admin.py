from django.contrib import admin

from apps.core.base.admin import BaseModelAdmin

from .models import Psychologist


@admin.register(Psychologist)
class PsychologistAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "full_name",
        "specialization",
        "experience_years",
        "price",
        "is_available",
        "created_at",
    )
    list_filter = ("is_available", "specialization")
    search_fields = ("first_name", "last_name", "phone_number", "specialization")
