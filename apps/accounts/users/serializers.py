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
            "is_staff",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_staff", "is_verified", "created_at", "updated_at"]
        related_fields = {"role": ["id", "name"]}


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
        self.fields[self.username_field] = serializers.CharField(validators=[phone_validator])

    def validate(self, attrs):
        data: dict = super().validate(attrs)
        user = self.user

        data["user"] = {
            "id": user.id,
            "phone_number": user.phone_number,
            "role": user.role.name if user.role else None,
        }

        return data
