from rest_framework import serializers

from apps.core.base.serializers import BaseModelSerializer

from .models import MESSAGE_CONTENT_MAX_LENGTH, ChatRoom, Message


class ChatRoomSerializer(BaseModelSerializer):
    # Joriy foydalanuvchi uchun suhbatdoshning ismi va asosiy rasmi — frontend
    # xona ro'yxatida "kim bilan" suhbat ekanini shu maydondan oladi.
    partner_info = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = "__all__"
        related_fields = {
            "match_request": ["id", "from_profile", "to_profile", "status"],
        }

    def get_partner_info(self, obj):
        """
        Xonaning ikkinchi ishtirokchisi (so'rov yuborayotgan foydalanuvchi
        emas) haqida qisqa ma'lumot: id, to'liq ism, asosiy rasm.

        Foydalanuvchi ma'lum bo'lmasa (masalan, schema generatsiyasi) yoki
        xodim moslik so'rovining hech qaysi tomoni bo'lmasa — None qaytadi.

        :param obj: Chat xonasi (ChatRoom).
        :return: {"id", "full_name", "main_photo"} yoki None (dict | None).
        """
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        match_request = obj.match_request
        if (
            not user
            or not getattr(user, "is_authenticated", False)
            or not match_request
        ):
            return None

        from_profile = match_request.from_profile
        to_profile = match_request.to_profile
        if from_profile and from_profile.user_id == user.id:
            partner = to_profile
        elif to_profile and to_profile.user_id == user.id:
            partner = from_profile
        else:
            return None

        if not partner:
            return None

        main_photo = next((p for p in partner.photos.all() if p.is_main), None)
        return {
            "id": partner.id,
            "full_name": f"{partner.first_name} {partner.last_name}".strip(),
            "main_photo": main_photo.image.url
            if main_photo and main_photo.image
            else None,
        }


class ChatRoomReadSerializer(serializers.Serializer):
    """`mark-read` amali uchun so'rov tanasi — qaysi xona o'qilgan qilinishi."""

    chat_room = serializers.PrimaryKeyRelatedField(queryset=ChatRoom.objects.active())


class MessageSerializer(BaseModelSerializer):
    # Javob berilayotgan xabar — faqat faol xabarlar qabul qilinadi. O'qishda
    # `reply_to_info` (qisqa oldindan ko'rinish) sifatida qaytadi.
    reply_to = serializers.PrimaryKeyRelatedField(
        queryset=Message.objects.active(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    # Uzunlik chegarasi va xatolik matni o'zbekcha bo'lishi uchun aniq e'lon
    # qilingan — avtomatik generatsiya qilingan maydon ingliz tilida xato beradi.
    content = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=MESSAGE_CONTENT_MAX_LENGTH,
        error_messages={
            "max_length": f"Xabar matni juda uzun (maksimal {MESSAGE_CONTENT_MAX_LENGTH} belgi)."
        },
    )

    class Meta:
        model = Message
        fields = "__all__"
        # sender doim so'rov yuborayotgan foydalanuvchidan olinadi — mijoz uni
        # yuborib, boshqa odam nomidan xabar yoza olmasligi kerak.
        read_only_fields = ["sender"]
        related_fields = {
            "sender": ["id", "phone_number", "email"],
            "chat_room": ["id"],
            "reply_to": {
                "fields": ["id", "sender", "content", "attachment", "created_at"]
            },
        }

    def validate(self, attrs):
        """
        Xabarda kamida matn yoki biriktirilgan fayl bo'lishi shart; `reply_to`
        berilsa u ayni chat xonasiga tegishli bo'lishi kerak.

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

        reply_to = attrs.get("reply_to")
        if reply_to is not None:
            chat_room = attrs.get(
                "chat_room",
                getattr(self.instance, "chat_room", None) if is_partial else None,
            )
            if chat_room is not None and reply_to.chat_room_id != chat_room.id:
                raise serializers.ValidationError(
                    "Javob berilayotgan xabar ushbu chat xonasiga tegishli emas."
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
