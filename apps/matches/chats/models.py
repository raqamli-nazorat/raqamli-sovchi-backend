from django.db import models

from apps.accounts.users.models import User
from apps.core.base.models import BaseModel
from apps.matches.match_requests.models import MatchRequest

MESSAGE_CONTENT_MAX_LENGTH = 256


class ChatRoom(BaseModel):
    match_request = models.ForeignKey(
        MatchRequest,
        on_delete=models.CASCADE,
        related_name="chat_rooms",
        verbose_name="Moslik so'rovi",
    )

    class Meta:
        verbose_name = "Chat xonasi"
        verbose_name_plural = "Chat xonalari"
        db_table = "chat_rooms"

    def __str__(self):
        return f"ChatRoom ({self.id}) - Match {self.match_request_id}"


class Message(BaseModel):
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Chat xonasi",
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name="Yuboruvchi",
    )
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="replies",
        blank=True,
        null=True,
        verbose_name="Javob berilgan xabar",
    )
    content = models.TextField(
        blank=True,
        default="",
        max_length=MESSAGE_CONTENT_MAX_LENGTH,
        verbose_name="Xabar matni",
    )
    attachment = models.FileField(
        upload_to="chat_attachments/",
        blank=True,
        null=True,
        verbose_name="Biriktirilgan fayl",
    )
    is_read = models.BooleanField(default=False, verbose_name="O'qilganligi")

    class Meta:
        verbose_name = "Xabar"
        verbose_name_plural = "Xabarlar"
        db_table = "messages"

    def __str__(self):
        return f"Message from {self.sender} in {self.chat_room_id}"
