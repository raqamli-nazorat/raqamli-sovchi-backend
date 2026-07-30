from django.contrib import admin
from apps.core.base.admin import BaseModelAdmin
from .models import LoginCode

@admin.register(LoginCode)
class LoginCodeAdmin(BaseModelAdmin):
    list_display = ("id", "phone_number", "code", "is_used", "expires_at", "created_at")
    list_filter = ("is_used",)
    search_fields = ("phone_number", "code")
    ordering = ("-created_at",)
