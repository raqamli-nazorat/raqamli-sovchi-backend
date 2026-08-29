from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.base.views import BaseManageViewSet
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer
from .services import filter_chat_rooms_for_user, filter_messages_for_user


class ChatRoomViewSet(BaseManageViewSet):
    serializer_class = ChatRoomSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["match_request"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = ChatRoom.objects.select_related(
            "match_request__from_profile__user",
            "match_request__to_profile__user",
        ).active()
        return filter_chat_rooms_for_user(qs, self.request.user)


class MessageViewSet(BaseManageViewSet):
    serializer_class = MessageSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["chat_room", "sender", "is_read"]
    search_fields = ["content"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = Message.objects.select_related(
            "sender",
            "chat_room__match_request__from_profile__user",
            "chat_room__match_request__to_profile__user",
        ).active()
        return filter_messages_for_user(qs, self.request.user)

    def perform_create(self, serializer):
        msg = serializer.save(sender=self.request.user)

        chat_room = msg.chat_room
        if chat_room and chat_room.match_request:
            mr = chat_room.match_request
            recipient_user = None
            if mr.from_profile and mr.from_profile.user_id != self.request.user.id:
                recipient_user = mr.from_profile.user
            elif mr.to_profile and mr.to_profile.user_id != self.request.user.id:
                recipient_user = mr.to_profile.user

            if recipient_user:
                from apps.accounts.notifications.models import Notification

                sender_name = getattr(
                    getattr(self.request.user, "profile", None),
                    "first_name",
                    "Foydalanuvchi",
                )
                Notification.objects.create(
                    user=recipient_user,
                    title=f"{sender_name}dan yangi xabar",
                    message=msg.content[:100],
                    extra_data={
                        "type": "new_chat_message",
                        "chat_room_id": str(chat_room.id),
                        "sender_id": str(self.request.user.id),
                    },
                )
