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


class ChatRoomReadSerializer(serializers.Serializer):
    """`mark-read` amali uchun so'rov tanasi — qaysi xona o'qilgan qilinishi."""

    chat_room = serializers.PrimaryKeyRelatedField(queryset=ChatRoom.objects.active())


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

    def validate(self, attrs):
        """
        Xabarda kamida matn yoki biriktirilgan fayl bo'lishi shart.

        :param attrs: Tekshiruvdan o'tgan maydonlar (dict).
        :return: O'zgarmagan attrs (dict).
        """
        is_partial = self.partial
        content = attrs.get(
            "content", getattr(self.instance, "content", "") if is_partial else ""
        )
        attachment = attrs.get(
            "attachment",
            getattr(self.instance, "attachment", None) if is_partial else None,
        )
        if not (content or "").strip() and not attachment:
            raise serializers.ValidationError(
                "Xabar bo'sh bo'lishi mumkin emas: matn yoki fayl biriktiring."
            )
        return attrs

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

        value = ChatRoom.objects.select_related(
            "match_request__from_profile",
            "match_request__to_profile",
        ).get(pk=value.pk)

        match_request = value.match_request
        if not match_request:
            raise serializers.ValidationError(
                "Ushbu chat xonasi moslik so'roviga bog'lanmagan."
            )

        from_user_id = (
            match_request.from_profile.user_id if match_request.from_profile else None
        )
        to_user_id = (
            match_request.to_profile.user_id if match_request.to_profile else None
        )

        if user.id not in (from_user_id, to_user_id):
            raise serializers.ValidationError(
                "Siz ushbu chat xonasining ishtirokchisi emassiz."
            )

        return value
