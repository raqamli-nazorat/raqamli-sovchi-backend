from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from apps.core.base.admin import BaseModelAdmin

from .models import Complaint, ComplaintStatus


@admin.register(Complaint)
class ComplaintAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "from_user",
        "to_user",
        "reason_display",
        "status_badge",
        "chat_room",
        "resolved_by",
        "created_at",
    )
    list_display_links = ("id", "from_user")
    list_filter = (
        "status",
        "reason",
        "created_at",
        "resolved_at",
    )
    search_fields = (
        "from_user__phone_number",
        "from_user__email",
        "to_user__phone_number",
        "to_user__email",
        "message",
        "admin_note",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "from_user",
        "to_user",
        "chat_room",
        "reason",
        "message",
        "evidence",
        "resolved_by",
        "resolved_at",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Shikoyat ma'lumotlari",
            {
                "fields": (
                    "from_user",
                    "to_user",
                    "chat_room",
                    "reason",
                    "message",
                )
            },
        ),
        (
            "Dalillar",
            {
                "fields": ("evidence",),
                "classes": ("collapse",),
            },
        ),
        (
            "Admin qarori",
            {
                "fields": (
                    "status",
                    "admin_note",
                    "resolved_by",
                    "resolved_at",
                )
            },
        ),
        (
            "Tizim ma'lumotlari",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def reason_display(self, obj):
        """Shikoyat sababining o'zbek matnini qaytaradi."""
        return obj.get_reason_display()

    reason_display.short_description = "Sabab"

    def status_badge(self, obj):
        """Holat tugmasini rang bilan ko'rsatadi."""
        colors = {
            ComplaintStatus.PENDING: "#FFC107",
            ComplaintStatus.APPROVED: "#28A745",
            ComplaintStatus.REJECTED: "#DC3545",
        }
        color = colors.get(obj.status, "#6C757D")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:12px;font-weight:600;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Holati"

    def save_model(self, request, obj, form, change):
        """Admin qarorini saqlashda resolved_by va resolved_at avtomatik to'ldiriladi."""
        if change and obj.status != ComplaintStatus.PENDING:
            if not obj.resolved_by_id:
                obj.resolved_by = request.user
            if not obj.resolved_at:
                obj.resolved_at = timezone.now()
        super().save_model(request, obj, form, change)
