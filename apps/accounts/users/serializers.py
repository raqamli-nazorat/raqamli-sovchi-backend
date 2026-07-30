from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.core.base.serializers import BaseModelSerializer
from .models import User, UserPledge


class UserSerializer(BaseModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "email",
            "auth_provider",
            "role",
            "is_verified",
            "is_staff",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_staff", "is_verified", "created_at", "updated_at"]


class UserPledgeSerializer(BaseModelSerializer):
    class Meta:
        model = UserPledge
        fields = "__all__"
        related_fields = {"user": ["id", "phone_number", "role"]}


class GoogleLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    phone_number = serializers.CharField()


class PhoneAuthSerializer(serializers.Serializer):
    phone_number = serializers.CharField()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data: dict = super().validate(attrs)
        user = self.user

        data["user"] = {
            "id": user.id,
            "phone_number": user.phone_number,
            "gender": user.profile.gender,
        }

        return data
