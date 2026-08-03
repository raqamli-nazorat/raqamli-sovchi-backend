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
        related_fields = {
            "sender": ["id", "phone_number", "email"],
            "chat_room": ["id"],
        }
