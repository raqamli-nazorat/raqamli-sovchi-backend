import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .presence import get_chat_partner_ids, mark_offline, mark_online, touch


class NotificationConsumer(AsyncWebsocketConsumer):
    """Bildirishnoma va onlayn holat uchun asosiy WebSocket ulanishi.

    Ilova ochiq turgan davomida ushlab turiladi. Ulanish/uzilishda foydalanuvchi
    onlayn holati yangilanadi va suhbatdoshlariga `presence` hodisasi yuboriladi.
    Mijoz ulanishni tirik ushlash uchun vaqti-vaqti bilan `{"type": "ping"}`
    yuboradi.
    """

    async def connect(self):
        user = self.scope.get("user")

        if not user or user.is_anonymous:
            await self.close(code=4003)
            return

        await self.accept()

        self.user_id = str(user.id)
        self.group_name = f"user_{user.id}_notifications"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        became_online = await database_sync_to_async(mark_online)(self.user_id)
        if became_online:
            await self._broadcast_presence("online", None)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        if hasattr(self, "user_id"):
            became_offline, last_seen = await database_sync_to_async(mark_offline)(
                self.user_id
            )
            if became_offline:
                await self._broadcast_presence("offline", last_seen)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or "{}")
        except (TypeError, ValueError):
            return

        if data.get("type") == "ping":
            if hasattr(self, "user_id"):
                revived = await database_sync_to_async(touch)(self.user_id)
                if revived:
                    await self._broadcast_presence("online", None)
            await self.send(text_data=json.dumps({"type": "pong"}))

    async def _broadcast_presence(self, status, last_seen):
        """Holat o'zgarishini suhbatdoshlarning bildirishnoma guruhlariga yuboradi."""
        partner_ids = await database_sync_to_async(get_chat_partner_ids)(self.user_id)
        payload = {
            "type": "presence",
            "user": self.user_id,
            "status": status,
            "last_seen": last_seen,
        }
        for partner_id in partner_ids:
            await self.channel_layer.group_send(
                f"user_{partner_id}_notifications",
                {"type": "presence_event", "payload": payload},
            )

    async def send_notification(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps(message))

    async def presence_event(self, event):
        """`group_send` -> socket: suhbatdoshning onlayn holati o'zgardi."""
        await self.send(text_data=json.dumps(event["payload"]))
