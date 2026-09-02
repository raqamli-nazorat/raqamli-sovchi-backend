from django.contrib import admin

from apps.core.base.admin import BaseModelAdmin

from .models import District, Region


@admin.register(Region)
class RegionAdmin(BaseModelAdmin):
    list_display = ("id", "name", "code", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(District)
class DistrictAdmin(BaseModelAdmin):
    list_display = ("id", "name", "code", "region", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("region", "is_active")
