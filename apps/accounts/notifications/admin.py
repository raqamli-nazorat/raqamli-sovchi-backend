from django.contrib import admin

from apps.core.base.admin import BaseModelAdmin as ModelAdmin

from .models import Notification, NotificationPreference, UserDevice


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "type",
        "title",
        "is_read",
        "created_at",
        "is_active",
    )
    list_display_links = ("id", "user")
    list_filter = ("type", "is_read", "created_at")
    search_fields = (
        "user__phone_number",
        "title",
        "message",
    )
    list_editable = ("is_read",)
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)

    fieldsets = (
        (
            "Asosiy ma'lumotlar",
            {
                "fields": (
                    "user",
                    "type",
                    "title",
                    "message",
                )
            },
        ),
        ("Texnik va Holat", {"fields": ("extra_data", "is_read")}),
        (
            "Tizim haqida ma'lumot",
            {
                "fields": ("created_at", "is_active"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "new_match",
        "new_message",
        "profile_viewed",
        "system_messages",
    )
    list_display_links = ("id", "user")
    search_fields = ("user__phone_number",)
    autocomplete_fields = ("user",)


@admin.register(UserDevice)
class UserDeviceAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "device_type",
        "device_id",
        "created_at",
        "is_active",
    )
    list_display_links = ("id", "user")
    list_filter = ("device_type", "created_at", "is_active")
    search_fields = (
        "user__full_name",
        "device_id",
        "fcm_token",
    )
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)
