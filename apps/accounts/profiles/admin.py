from django.contrib import admin
from django.utils.html import format_html
from apps.core.base.admin import BaseModelAdmin
from .models import Profile, ProfilePhoto, RepresentativeInfo
from .utils import is_female_candidate


class ProfilePhotoInline(admin.TabularInline):
    model = ProfilePhoto
    extra = 1
    fields = ("image_display", "is_main", "order")
    readonly_fields = ("image_display",)

    def image_display(self, obj):
        if not obj or not obj.id:
            return "-"
        if is_female_candidate(obj.profile):
            return format_html(
                '<span style="color: #d9534f; font-weight: bold;">🔒 Maxfiy (Kelin rasmi - Adminlar uchun ham yopiq)</span>'
            )
        if obj.image:
            return format_html('<img src="{}" style="height: 60px; border-radius: 4px;" />', obj.image.url)
        return "-"

    image_display.short_description = "Rasm ko'rinishi"


class RepresentativeInfoInline(admin.StackedInline):
    model = RepresentativeInfo
    extra = 0


@admin.register(Profile)
class ProfileAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "user",
        "candidate_type",
        "gender",
        "birth_year",
        "region",
        "district",
        "education_level",
        "nationality",
        "profession",
        "health_status",
        "marital_status",
        "has_children",
        "blur_photos",
        "created_at",
    )
    list_filter = (
        "candidate_type",
        "gender",
        "health_status",
        "marital_status",
        "education_level",
        "nationality",
        "profession",
        "has_children",
        "blur_photos",
        "region",
        "district",
    )
    search_fields = ("first_name", "last_name", "user__phone_number")
    inlines = [ProfilePhotoInline, RepresentativeInfoInline]


@admin.register(ProfilePhoto)
class ProfilePhotoAdmin(BaseModelAdmin):
    list_display = ("id", "profile", "image_display", "is_main", "order", "created_at")
    readonly_fields = ("image_display",)
    list_filter = ("is_main",)

    def image_display(self, obj):
        if not obj:
            return "-"
        if is_female_candidate(obj.profile):
            return format_html(
                '<span style="color: #d9534f; font-weight: bold;">🔒 Maxfiy (Kelin rasmi - Adminlar uchun ham yopiq)</span>'
            )
        if obj.image:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="height: 80px; border-radius: 4px;" /></a>', obj.image.url, obj.image.url)
        return "-"

    image_display.short_description = "Rasm ko'rinishi"


@admin.register(RepresentativeInfo)
class RepresentativeInfoAdmin(BaseModelAdmin):
    list_display = ("id", "profile", "kinship", "candidate_role", "created_at")
    list_filter = ("kinship", "candidate_role")
