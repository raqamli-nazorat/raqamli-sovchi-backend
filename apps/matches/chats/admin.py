from django.contrib import admin

from apps.core.base.admin import BaseModelAdmin

from .models import ChatRoom, Message


@admin.register(ChatRoom)
class ChatRoomAdmin(BaseModelAdmin):
    list_display = ("id", "match_request", "created_at")


@admin.register(Message)
class MessageAdmin(BaseModelAdmin):
    list_display = ("id", "chat_room", "sender", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("content", "sender__phone_number", "sender__email")
