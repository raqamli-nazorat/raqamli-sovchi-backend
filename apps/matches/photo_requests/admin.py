from django.contrib import admin

from apps.core.base.admin import BaseModelAdmin

from .models import PhotoRequest


@admin.register(PhotoRequest)
class PhotoRequestAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "from_profile",
        "to_profile",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = (
        "from_profile__first_name",
        "from_profile__last_name",
        "to_profile__first_name",
        "to_profile__last_name",
    )
