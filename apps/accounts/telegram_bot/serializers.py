from rest_framework import serializers

from apps.core.base.serializers import BaseModelSerializer
from apps.core.utils.validators import phone_validator
from .models import LoginCode


class LoginCodeSerializer(BaseModelSerializer):
    phone_number = serializers.CharField(validators=[phone_validator])

    class Meta:
        model = LoginCode
        fields = ["id", "phone_number", "is_used", "expires_at", "created_at"]
        read_only_fields = ["id", "is_used", "expires_at", "created_at"]


class VerifyCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(validators=[phone_validator])
    code = serializers.CharField(max_length=6, min_length=6)
