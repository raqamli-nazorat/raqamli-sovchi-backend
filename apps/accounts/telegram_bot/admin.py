from django.contrib import admin

from apps.core.base.admin import BaseModelAdmin

from .models import TelegramAuthSession


@admin.register(TelegramAuthSession)
class TelegramAuthSessionAdmin(BaseModelAdmin):
    list_display = ("id", "session_id", "status", "user", "expires_at", "created_at")
    list_filter = ("status",)
    search_fields = ("session_id", "user__phone_number")
    ordering = ("-created_at",)
