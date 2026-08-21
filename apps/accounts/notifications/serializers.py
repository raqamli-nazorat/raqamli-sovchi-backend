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


class WebSocketTicketResponseSerializer(serializers.Serializer):
    ticket = serializers.UUIDField(help_text="WebSocket ulanish chiptasi")
    expires_in = serializers.IntegerField(
        default=60, help_text="Chiptaning amal qilish muddati (soniya)"
    )


class NotificationCountSerializer(serializers.Serializer):
    unread = serializers.IntegerField(help_text="O'qilmagan bildirishnomalar soni")
    read = serializers.IntegerField(help_text="O'qilgan bildirishnomalar soni")
    total = serializers.IntegerField(help_text="Jami bildirishnomalar soni")
