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
    phone_number = serializers.CharField(
        validators=[phone_validator],
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    display_id = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    candidate_type = serializers.SerializerMethodField()
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
            "telegram_id",
            "candidate_type",
            "completion_percentage",
            "status",
            "role",
            "profile",
            "auth_provider",
            "is_verified",
            "is_blocked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "telegram_id",
            "is_verified",
            "auth_provider",
            "profile",
            "created_at",
            "updated_at",
        ]
        related_fields = {
            "role": ["id", "name"],
            "profile": {
                "exclude": ["user"],
                "related_fields": {
                    "region": ["id", "name"],
                    "district": ["id", "name"],
                    "photos": ["id", "image", "is_main", "order", "created_at"],
                    "health_status": ["id", "name"],
                    "marital_status": ["id", "name"],
                },
            },
        }

    def get_display_id(self, obj):
        short_code = str(obj.id).replace("-", "")[:5].upper()
        return f"USR-{short_code}"

    def get_full_name(self, obj):
        profile = getattr(obj, "profile", None)
        if profile and (profile.first_name or profile.last_name):
            return f"{profile.first_name or ''} {profile.last_name or ''}".strip()
        return obj.phone_number or obj.email or ""

    def get_candidate_type(self, obj):
        profile = getattr(obj, "profile", None)
        if profile and profile.candidate_type:
            return profile.get_candidate_type_display()
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

        pct = self.get_completion_percentage(obj)
        if pct < 50:
            return "Anketa to'liq emas"

        if not obj.is_verified:
            return "Tekshiruvda"

        return "Tasdiqlangan"


class UserPledgeSerializer(BaseModelSerializer):
    class Meta:
        model = UserPledge
        fields = "__all__"
        related_fields = {"user": ["id", "phone_number"]}


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Google ID token (from google_sign_in Flutter package: GoogleSignInAuthentication.idToken)",
    )
    authorization_code = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Google OAuth authorization code (serverAuthCode) — alternative to id_token",
    )
    redirect_uri = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
        help_text="redirect_uri — only needed when using authorization_code on web ('postmessage').",
    )

    def validate(self, attrs):
        if not attrs.get("id_token") and not attrs.get("authorization_code"):
            raise serializers.ValidationError(
                "id_token yoki authorization_code yuborilishi shart."
            )
        return attrs


class PhoneAuthSerializer(serializers.Serializer):
    phone_number = serializers.CharField(validators=[phone_validator])


class EmailAuthSerializer(serializers.Serializer):
    email = serializers.EmailField()


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

        if user.is_blocked:
            raise serializers.ValidationError(
                {"detail": "Sizning hisobingiz bloklangan."}
            )

        data["user"] = {
            "id": user.id,
            "phone_number": user.phone_number,
            "role": user.role.name if user.role else None,
        }

        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={
            "min_length": "Parol kamida 8 ta raqamdan iborat bo'lishi kerak."
        },
    )

    confirm_new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Eski parol noto'g'ri.")
        return value

    def validate(self, attrs):
        new_password = attrs.get("new_password")
        confirm_new_password = attrs.get("confirm_new_password")
        old_password = attrs.get("old_password")

        if new_password != confirm_new_password:
            raise serializers.ValidationError(
                {"new_password": "Yangi parol maydonlari mos kelmadi."}
            )

        if old_password == new_password:
            raise serializers.ValidationError(
                {"new_password": "Yangi parol eskisidan farq qilishi kerak."}
            )

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
