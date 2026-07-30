from django.contrib import admin
from unfold.admin import ModelAdmin


class BaseModelAdmin(ModelAdmin):
    def delete_model(self, request, obj):
        obj.delete()

    def delete_queryset(self, request, queryset):
        queryset.delete()

    actions = ["really_hard_delete"]

    @admin.action(description="Butunlay o'chirish")
    def really_hard_delete(self, request, queryset):
        count = queryset.count()

        if hasattr(queryset, "hard_delete"):
            queryset.hard_delete()
        else:
            queryset.delete()

        self.message_user(
            request,
            f"Muvaqqiyatli: {count} ta ob'yekt bazadan butunlay o'chirib yuborildi.",
        )
