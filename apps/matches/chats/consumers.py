import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Chat xonasi uchun WebSocket — `ws/chat/<room_id>/?ticket=...`.

    Autentifikatsiya `TicketAuthMiddleware` orqali (60 soniyalik ticket).
    Xabarlar REST orqali yaratiladi, bu yerda faqat jonli tarqatiladi:
    yangi xabar (`message`) va "yozyapti" (`typing`) hodisalari.
    """

    async def connect(self):
        user = self.scope.get("user")
        if (
            not user
            or user.is_anonymous
            or not getattr(user, "is_active", False)
            or getattr(user, "is_blocked", False)
        ):
            await self.close(code=4003)
            return

        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        if not await self._is_participant(user, self.room_id):
            await self.close(code=4003)
            return

        self.group_name = f"chat_{self.room_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not hasattr(self, "group_name"):
            return
        try:
            data = json.loads(text_data or "{}")
        except (TypeError, ValueError):
            await self._error("Yaroqsiz JSON.")
            return

        msg_type = data.get("type")

        if msg_type == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "chat_typing", "sender": str(self.scope["user"].id)},
            )
            return

        if msg_type == "message":
            content = (data.get("content") or "").strip()
            if not content:
                await self._error("Xabar matni bo'sh bo'lishi mumkin emas.")
                return
            try:
                message = await self._persist_message(content, data.get("reply_to"))
            except ValueError as exc:
                await self._error(str(exc))
                return
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "chat_message", "message": self._payload(message)},
            )
            return

        await self._error("Noma'lum 'type'. Kutilgan: 'message' yoki 'typing'.")

    async def _error(self, detail):
        await self.send(text_data=json.dumps({"type": "error", "detail": detail}))

    async def chat_message(self, event):
        """`group_send` -> socket: yangi xabar."""
        await self.send(
            text_data=json.dumps({"type": "message", "message": event["message"]})
        )

    async def chat_typing(self, event):
        """`group_send` -> socket: boshqa ishtirokchi yozmoqda (o'ziga qaytarilmaydi)."""
        if event.get("sender") == str(self.scope["user"].id):
            return
        await self.send(
            text_data=json.dumps({"type": "typing", "sender": event["sender"]})
        )

    @staticmethod
    def _payload(message):
        """Xabarni WS uchun dict ko'rinishiga keltiradi (DB'ga tegmaydi)."""
        from .services import build_message_payload

        return build_message_payload(message)

    @database_sync_to_async
    def _is_participant(self, user, room_id):
        """Foydalanuvchi shu xonaning ishtirokchisi (yoki xodim) ekanini tekshiradi."""
        from .models import ChatRoom
        from .services import filter_chat_rooms_for_user

        qs = filter_chat_rooms_for_user(ChatRoom.objects.active(), user)
        return qs.filter(pk=room_id).exists()

    @database_sync_to_async
    def _persist_message(self, content, reply_to_id=None):
        """Xabarni bazaga yozadi va qabul qiluvchiga bildirishnoma yaratadi."""
        from .models import ChatRoom
        from .services import persist_chat_message

        room = ChatRoom.objects.get(pk=self.room_id)
        return persist_chat_message(room, self.scope["user"], content, reply_to_id)
