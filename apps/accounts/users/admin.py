from django.contrib import admin
from unfold.admin import ModelAdmin
from apps.core.base.admin import BaseModelAdmin
from .models import User, UserPledge


@admin.register(User)
class UserAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "phone_number",
        "email",
        "role",
        "auth_provider",
        "is_verified",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "auth_provider", "is_verified", "is_staff", "is_active")
    search_fields = ("phone_number", "email", "first_name", "last_name")
    ordering = ("-created_at",)


@admin.register(UserPledge)
class UserPledgeAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "user",
        "accepted_terms",
        "has_serious_badge",
        "ip_address",
        "created_at",
    )
    list_filter = ("accepted_terms", "has_serious_badge")
    search_fields = ("user__phone_number", "user__email", "ip_address")
