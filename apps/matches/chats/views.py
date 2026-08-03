from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.base.views import BaseManageViewSet
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer


class ChatRoomViewSet(BaseManageViewSet):
    queryset = ChatRoom.objects.select_related("match_request").active()
    serializer_class = ChatRoomSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["match_request"]
    ordering_fields = ["created_at"]


class MessageViewSet(BaseManageViewSet):
    queryset = Message.objects.select_related("chat_room", "sender").active()
    serializer_class = MessageSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["chat_room", "sender", "is_read"]
    search_fields = ["content"]
    ordering_fields = ["created_at"]
