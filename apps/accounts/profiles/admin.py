from django.contrib import admin
from apps.core.base.admin import BaseModelAdmin
from .models import Profile, ProfilePhoto, RepresentativeInfo


class ProfilePhotoInline(admin.TabularInline):
    model = ProfilePhoto
    extra = 1


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
    list_display = ("id", "profile", "is_main", "order", "created_at")
    list_filter = ("is_main",)


@admin.register(RepresentativeInfo)
class RepresentativeInfoAdmin(BaseModelAdmin):
    list_display = ("id", "profile", "kinship", "candidate_role", "created_at")
    list_filter = ("kinship", "candidate_role")
