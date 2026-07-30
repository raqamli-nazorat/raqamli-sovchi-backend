from django.contrib.auth.models import Permission
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.core.base.serializers import BaseModelSerializer
from apps.core.utils.validators import phone_validator
from .models import Role, User, UserPledge


class PermissionSerializer(serializers.ModelSerializer):
    model_name = serializers.CharField(source="content_type.model", read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "model_name"]

    def get_name(self, obj):
        action = obj.codename.split("_")[0]
        model_name = obj.content_type.name.capitalize()

        mapping = {
            "add": f"{model_name} qo'shish",
            "change": f"{model_name} tahrirlash",
            "delete": f"{model_name} o'chirish",
            "view": f"{model_name} ko'rish",
        }
        return mapping.get(action, obj.name)


class RoleSerializer(BaseModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"


class UserSerializer(BaseModelSerializer):
    phone_number = serializers.CharField(validators=[phone_validator])

    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "email",
            "role",
            "auth_provider",
            "is_verified",
            "is_blocked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_verified", "created_at", "updated_at"]
        related_fields = {
            "role": ["id", "name"],
            "profile": "__all__",
        }


class UserListSerializer(BaseModelSerializer):
    display_id = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    candidate_type = serializers.SerializerMethodField()
    region_name = serializers.SerializerMethodField()
    completion_percentage = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "display_id",
            "full_name",
            "phone_number",
            "email",
            "candidate_type",
            "region_name",
            "completion_percentage",
            "status",
            "is_verified",
            "is_blocked",
            "created_at",
        ]

    def get_display_id(self, obj):
        short_code = str(obj.id).replace("-", "")[:5].upper()
        return f"USR-{short_code}"

    def get_full_name(self, obj):
        profile = getattr(obj, "profile", None)
        if profile and (profile.first_name or profile.last_name):
            return f"{profile.first_name or ''} {profile.last_name or ''}".strip()
        return obj.phone_number

    def get_candidate_type(self, obj):
        profile = getattr(obj, "profile", None)
        if profile and profile.candidate_type:
            return profile.get_candidate_type_display()
        return None

    def get_region_name(self, obj):
        profile = getattr(obj, "profile", None)
        if profile and profile.region:
            return profile.region.name
        return None

    def get_completion_percentage(self, obj):
        profile = getattr(obj, "profile", None)
        if not profile:
            return 0

        score = 0
        if profile.first_name:
            score += 10
        if profile.last_name:
            score += 10
        if profile.gender:
            score += 10
        if profile.candidate_type:
            score += 10
        if profile.birth_year:
            score += 10
        if profile.height and profile.weight:
            score += 10
        if profile.region:
            score += 10
        if profile.district:
            score += 10
        if profile.marital_status:
            score += 10
        if hasattr(profile, "photos") and bool(profile.photos.all()):
            score += 10

        return score

    def get_status(self, obj):
        if obj.is_blocked:
            return "Bloklangan"
        if obj.is_verified:
            return "Tasdiqlangan"

        pct = self.get_completion_percentage(obj)
        if pct < 50:
            return "Anketa to'liq emas"

        return "Tekshiruvda"


class UserPledgeSerializer(BaseModelSerializer):
    class Meta:
        model = UserPledge
        fields = "__all__"
        related_fields = {"user": ["id", "phone_number"]}


class GoogleLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    phone_number = serializers.CharField(validators=[phone_validator])


class PhoneAuthSerializer(serializers.Serializer):
    phone_number = serializers.CharField(validators=[phone_validator])


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "phone_number"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField(
            validators=[phone_validator]
        )

    def validate(self, attrs):
        data: dict = super().validate(attrs)
        user = self.user

        data["user"] = {
            "id": user.id,
            "phone_number": user.phone_number,
            "role": user.role.name if user.role else None,
        }

        return data
