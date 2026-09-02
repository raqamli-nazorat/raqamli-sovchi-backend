from rest_framework import serializers

from .models import Notification, UserDevice


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "title",
            "message",
            "extra_data",
            "is_read",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ("id", "user", "fcm_token", "device_type", "device_id", "created_at")
        read_only_fields = ("id", "user", "created_at")
        extra_kwargs = {
            "fcm_token": {"validators": []},
            "device_id": {"validators": []},
        }


class UserDeviceRegisterSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(
        required=True, help_text="FCM push bildirishnoma tokeni"
    )
    device_type = serializers.ChoiceField(
        choices=[("ios", "iOS"), ("android", "Android"), ("web", "Web")],
        required=True,
        help_text="Qurilma turi",
    )
    device_id = serializers.CharField(
        required=True, help_text="Qurilmaning unikal identifikatori"
    )


class UserDeviceUnregisterSerializer(serializers.Serializer):
    device_id = serializers.CharField(
        required=True, help_text="O'chirilayotgan qurilmaning unikal identifikatori"
    )
