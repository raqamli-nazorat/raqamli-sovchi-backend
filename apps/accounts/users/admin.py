from django.contrib import admin
from unfold.admin import ModelAdmin
from apps.core.base.admin import BaseModelAdmin
from .models import User, UserPledge, Role, BlockedFace, UserDevice
from apps.core.utils.face import register_user_faces_as_blocked


@admin.register(Role)
class RoleAdmin(BaseModelAdmin):
    list_display = ("id", "name", "is_default", "created_at")
    list_filter = ("is_default",)
    search_fields = ("name",)
    filter_horizontal = ("permissions",)


@admin.register(User)
class UserAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "phone_number",
        "email",
        "role",
        "auth_provider",
        "is_verified",
        "is_blocked",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = (
        "role",
        "auth_provider",
        "is_verified",
        "is_blocked",
        "is_staff",
        "is_active",
    )
    search_fields = (
        "phone_number",
        "email",
        "profile__first_name",
        "profile__last_name",
    )
    ordering = ("-created_at",)

    def save_model(self, request, obj, form, change):
        if obj.password and not obj.password.startswith("pbkdf2_"):
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)
        if obj.is_blocked:
            register_user_faces_as_blocked(obj, reason="Admin paneli orqali bloklandi")
        else:
            from apps.core.utils.face import remove_user_faces_from_blocked

            remove_user_faces_from_blocked(obj)


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


@admin.register(BlockedFace)
class BlockedFaceAdmin(BaseModelAdmin):
    list_display = ("id", "user", "reason", "created_at")
    search_fields = ("user__phone_number", "user__email", "reason")


@admin.register(UserDevice)
class UserDeviceAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "user",
        "device_name",
        "device_os",
        "device_id",
        "ip_address",
        "last_active",
        "is_active",
    )
    list_filter = ("is_active", "device_os")
    search_fields = (
        "user__phone_number",
        "user__email",
        "device_name",
        "device_id",
        "ip_address",
    )
