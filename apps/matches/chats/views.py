from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.accounts.notifications.presence import get_chat_partner_ids, get_presence
from apps.accounts.profiles.models import ProfilePhoto
from apps.core.base.views import BaseManageViewSet, BaseReadOnlyViewSet

from .models import ChatRoom, Message
from .serializers import ChatRoomReadSerializer, ChatRoomSerializer, MessageSerializer
from .services import (
    _is_staff_user,
    broadcast_new_message,
    count_unread_messages,
    filter_chat_rooms_for_user,
    filter_messages_for_user,
    mark_room_messages_read,
    notify_recipient_new_message,
)


class ChatRoomViewSet(BaseReadOnlyViewSet):
    """
    Chat xonalari — faqat o'qish uchun.

    Xona faqat `MatchRequest` qabul qilinganda avtomatik ochiladi
    (`match_requests.accept_request`), API orqali yaratilmaydi.
    """

    serializer_class = ChatRoomSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["match_request"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        # `partner_info` (ism + asosiy rasm) uchun faqat is_main=True rasm
        # oldindan yuklanadi — aks holda har xona uchun alohida so'rov ketardi (N+1).
        main_photo_qs = ProfilePhoto.objects.filter(is_main=True)
        qs = (
            ChatRoom.objects.select_related(
                "match_request__from_profile__user",
                "match_request__to_profile__user",
            )
            .prefetch_related(
                Prefetch("match_request__from_profile__photos", queryset=main_photo_qs),
                Prefetch("match_request__to_profile__photos", queryset=main_photo_qs),
            )
            .active()
        )
        return filter_chat_rooms_for_user(qs, self.request.user)

    @extend_schema(
        summary="Suhbatdoshning onlayn holati",
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=["get"], url_path="presence")
    def presence(self, request, pk=None):
        """Ushbu xonadagi ikkinchi ishtirokchining hozirgi onlayn holati."""
        room = self.get_object()
        mr = room.match_request
        from_id = mr.from_profile.user_id if mr and mr.from_profile else None
        to_id = mr.to_profile.user_id if mr and mr.to_profile else None
        partner_id = to_id if str(from_id) == str(request.user.id) else from_id
        if not partner_id:
            raise NotFound("Suhbatdosh topilmadi.")
        return Response(get_presence(partner_id))

    @extend_schema(
        summary="Barcha suhbatdoshlarning onlayn holati",
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=["get"], url_path="presence")
    def presence_all(self, request):
        """Foydalanuvchining barcha suhbatdoshlari holati (chat ro'yxati ekrani uchun)."""
        partner_ids = get_chat_partner_ids(request.user.id)
        return Response({pid: get_presence(pid) for pid in partner_ids})


class MessageViewSet(BaseManageViewSet):
    serializer_class = MessageSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["chat_room", "sender", "is_read"]
    search_fields = ["content"]
    ordering_fields = ["created_at"]
    # Chat oynasi uchun eski xabar tepada bo'lishi kerak (BaseModel default
    # `-created_at` ni bekor qiladi). Mijoz `?ordering=-created_at` bilan
    # teskarisini so'rashi mumkin.
    ordering = ["created_at"]

    def get_queryset(self):
        qs = Message.objects.select_related(
            "sender",
            "reply_to",
            "reply_to__sender",
            "chat_room__match_request__from_profile__user",
            "chat_room__match_request__to_profile__user",
        ).active()
        return filter_messages_for_user(qs, self.request.user)

    def perform_update(self, serializer):
        """
        Xabarni faqat uni yozgan foydalanuvchi tahrirlashi mumkin.

        Begona ishtirokchi (masalan, qabul qiluvchi) faqat `is_read` ni
        belgilay oladi — xona ID si ma'lum bo'lgan tomon boshqa odamning
        xabar matnini o'zgartirib qo'ymasligi kerak.

        :param serializer: Tekshiruvdan o'tgan MessageSerializer.
        """
        instance = serializer.instance
        if (
            not _is_staff_user(self.request.user)
            and instance.sender_id != self.request.user.id
        ):
            changed_fields = set(serializer.validated_data.keys())
            if not changed_fields.issubset({"is_read"}):
                raise PermissionDenied(
                    "Faqat o'zingiz yozgan xabarni tahrirlashingiz mumkin."
                )
        serializer.save()

    def perform_destroy(self, instance):
        """
        Xabarni faqat uni yozgan foydalanuvchi (yoki xodim) o'chira oladi.

        :param instance: O'chirilayotgan Message obyekti.
        """
        if (
            not _is_staff_user(self.request.user)
            and instance.sender_id != self.request.user.id
        ):
            raise PermissionDenied(
                "Faqat o'zingiz yozgan xabarni o'chirishingiz mumkin."
            )
        instance.delete()

    def perform_create(self, serializer):
        """Xabarni saqlaydi, qabul qiluvchiga bildirishnoma yozadi va WS'ga uzatadi."""
        msg = serializer.save(sender=self.request.user)
        notify_recipient_new_message(msg)
        broadcast_new_message(msg)

    @extend_schema(
        summary="Xonadagi barcha xabarlarni o'qilgan deb belgilash",
        request=ChatRoomReadSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=["post"], url_path="mark-read")
    def mark_read(self, request):
        """Ko'rsatilgan xonadagi, boshqa ishtirokchi yozgan xabarlarni o'qilgan qiladi."""
        serializer = ChatRoomReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chat_room = serializer.validated_data["chat_room"]

        allowed = filter_chat_rooms_for_user(ChatRoom.objects.active(), request.user)
        if not allowed.filter(pk=chat_room.pk).exists():
            raise PermissionDenied("Siz ushbu chat xonasining ishtirokchisi emassiz.")

        updated = mark_room_messages_read(chat_room, request.user)
        return Response({"marked_read": updated})

    @extend_schema(
        summary="O'qilmagan xabarlar soni",
        parameters=[
            OpenApiParameter(
                "chat_room", OpenApiTypes.UUID, required=False, description="Xona ID si"
            )
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        """Foydalanuvchi uchun o'qilmagan xabarlar soni (ixtiyoriy: bitta xona bo'yicha)."""
        chat_room = None
        room_id = request.query_params.get("chat_room")
        if room_id:
            chat_room = ChatRoom.objects.active().filter(pk=room_id).first()
            if not chat_room:
                raise NotFound("Chat xonasi topilmadi.")

        count = count_unread_messages(request.user, chat_room)
        return Response({"unread": count})
