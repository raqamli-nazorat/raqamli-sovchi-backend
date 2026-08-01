from rest_framework import serializers

from apps.core.base.serializers import BaseModelSerializer
from .models import TelegramAuthSession
from .utils import get_bot_username


class TelegramAuthSessionSerializer(BaseModelSerializer):
    bot_url = serializers.SerializerMethodField()

    class Meta:
        model = TelegramAuthSession
        fields = ["session_id", "status", "bot_url", "expires_at", "created_at"]

    def get_bot_url(self, obj):
        bot_username = get_bot_username()
        return f"https://t.me/{bot_username}?start={obj.session_id}"
