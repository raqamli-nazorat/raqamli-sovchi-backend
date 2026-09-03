from django.contrib.auth.models import Permission
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.core.base.serializers import BaseModelSerializer
from apps.core.utils.validators import phone_validator

from .models import BlockedUser, Role, User, UserDevice, UserPledge


class PermissionSerializer(BaseModelSerializer):
    model_name = serializers.CharField(source="content_type.model", read_only=True)
    group_label = serializers.CharField(source="content_type.name", read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "model_name", "group_label"]

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


class RolePermissionSerializer(BaseModelSerializer):
    model_name = serializers.CharField(source="content_type.model", read_only=True)
    group_label = serializers.CharField(source="content_type.name", read_only=True)

    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "model_name", "group_label"]


class RoleSerializer(BaseModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), required=False
    )
    permissions_info = RolePermissionSerializer(
        source="permissions", many=True, read_only=True
    )

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "is_default",
            "permissions",
            "permissions_info",
            "created_at",
            "updated_at",
        ]


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
    region_name = serializers.SerializerMethodField()
    district_name = serializers.SerializerMethodField()
    main_photo = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "display_id",
            "full_name",
            "main_photo",
            "phone_number",
            "email",
            "telegram_id",
            "candidate_type",
            "age",
            "region_name",
            "district_name",
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

    def get_age(self, obj):
        """Profildan tug'ilgan sanaga asoslanib yoshni hisoblaydi."""
        from datetime import date

        profile = getattr(obj, "profile", None)
        if not profile or not profile.birth_date:
            return None
        today = date.today()
        bd = profile.birth_date
        return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

    def get_region_name(self, obj):
        profile = getattr(obj, "profile", None)
        if profile and profile.region_id:
            return profile.region.name
        return None

    def get_district_name(self, obj):
        profile = getattr(obj, "profile", None)
        if profile and profile.district_id:
            return profile.district.name
        return None

    def get_main_photo(self, obj):
        profile = getattr(obj, "profile", None)
        if not profile or not profile.pk:
            return None
        photos = profile.photos.all()
        main = next((p for p in photos if p.is_main), None) or next(iter(photos), None)
        if main and main.image:
            request = self.context.get("request")
            return (
                request.build_absolute_uri(main.image.url)
                if request
                else main.image.url
            )
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
        if profile.birth_date:
            score += 10
        if profile.height and profile.weight:
            score += 10
        if profile.region:
            score += 10
        if profile.district:
            score += 10
        if profile.marital_status:
            score += 10
        if (
            profile
            and profile.pk
            and hasattr(profile, "photos")
            and bool(profile.photos.all())
        ):
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
        # user view ichida so'rov yuboruvchidan qo'yiladi (perform_create),
        # shuning uchun mijozdan talab qilinmaydi.
        read_only_fields = ["user"]
        related_fields = {"user": ["id", "phone_number"]}


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(
        help_text="Google ID token (GoogleSignInAuthentication.idToken — works for both mobile and web)",
    )


class PhoneAuthSerializer(serializers.Serializer):
    phone_number = serializers.CharField(validators=[phone_validator])


class EmailAuthSerializer(serializers.Serializer):
    email = serializers.EmailField()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "phone_number"

    def get_token(self, user):
        token = super().get_token(user)
        request = (
            getattr(self, "context", {}).get("request")
            if hasattr(self, "context")
            else None
        )
        if request:
            device_id = request.headers.get("X-Device-Id") or request.META.get(
                "HTTP_X_DEVICE_ID"
            )
            if device_id:
                token["device_id"] = str(device_id)
        return token

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

        request = self.context.get("request")
        if request:
            from apps.accounts.users.services import register_or_update_user_device

            register_or_update_user_device(user, request)

        return data


class UserDeviceSerializer(BaseModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserDevice
        fields = [
            "id",
            "device_id",
            "device_name",
            "device_os",
            "ip_address",
            "last_active",
            "is_active",
            "is_current",
            "created_at",
        ]

    def get_is_current(self, obj):
        request = self.context.get("request")
        if not request:
            return False
        current_device_id = request.headers.get("X-Device-Id") or request.META.get(
            "HTTP_X_DEVICE_ID"
        )
        return obj.device_id == current_device_id


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


class BlockedUserSerializer(BaseModelSerializer):
    class Meta:
        model = BlockedUser
        fields = ["id", "blocker", "blocked", "reason", "created_at"]
        read_only_fields = ["id", "blocker", "created_at"]
        related_fields = {
            "blocked": [
                "id",
                "phone_number",
                "email",
                "profile",
            ]
        }
