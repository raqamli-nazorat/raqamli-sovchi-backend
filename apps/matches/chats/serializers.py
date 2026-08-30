from rest_framework import serializers

from apps.core.base.serializers import BaseModelSerializer

from .models import ChatRoom, Message


class ChatRoomSerializer(BaseModelSerializer):
    class Meta:
        model = ChatRoom
        fields = "__all__"
        related_fields = {
            "match_request": ["id", "from_profile", "to_profile", "status"],
        }


class MessageSerializer(BaseModelSerializer):
    class Meta:
        model = Message
        fields = "__all__"
        # sender doim so'rov yuborayotgan foydalanuvchidan olinadi — mijoz uni
        # yuborib, boshqa odam nomidan xabar yoza olmasligi kerak.
        read_only_fields = ["sender"]
        related_fields = {
            "sender": ["id", "phone_number", "email"],
            "chat_room": ["id"],
        }

    def validate_chat_room(self, value):
        """
        Foydalanuvchi faqat o'zi ishtirok etayotgan xonaga xabar yoza olishini tekshiradi.

        Xona ID si ma'lum bo'lgan begona odam yozib qo'ymasligi uchun kerak:
        o'qish tomoni get_queryset bilan yopilgan, yozish tomoni esa shu yerda.

        :param value: Chat xonasi (ChatRoom).
        :return: Tekshiruvdan o'tgan chat xonasi (ChatRoom).
        """
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return value

        if user.is_staff or user.is_superuser:
            return value

        match_request = value.match_request
        if not match_request:
            raise serializers.ValidationError(
                "Ushbu chat xonasi moslik so'roviga bog'lanmagan."
            )

        participant_ids = {
            match_request.from_profile.user_id if match_request.from_profile else None,
            match_request.to_profile.user_id if match_request.to_profile else None,
        }
        if user.id not in participant_ids:
            raise serializers.ValidationError(
                "Siz ushbu chat xonasining ishtirokchisi emassiz."
            )

        return value
