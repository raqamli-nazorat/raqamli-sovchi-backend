import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q

from .models import Message

logger = logging.getLogger(__name__)


def _is_staff_user(user):
    """
    Foydalanuvchi xodim (moderator/admin) rolida ekanini aniqlaydi.

    :param user: Tekshirilayotgan foydalanuvchi (User).
    :return: Xodim bo'lsa True, aks holda False (bool).
    """
    return bool(
        user.is_staff or user.is_superuser or (user.role and not user.role.is_default)
    )


def filter_chat_rooms_for_user(qs, user):
    """
    Foydalanuvchi kira oladigan chat xonalarini filtrlaydi.

    Chat faqat moslik so'rovining ikki tomoni uchun ochiq: so'rovni yuborgan
    va qabul qilgan nomzodlar. Vakil chatni o'qiy olmaydi.

    :param qs: Asosiy chat xonalari QuerySet-i.
    :param user: So'rov yuborayotgan foydalanuvchi (User).
    :return: Filtrlangan QuerySet.
    """
    if not user or not user.is_authenticated:
        return qs.none()

    if _is_staff_user(user):
        return qs

    return qs.filter(
        Q(match_request__from_profile__user=user)
        | Q(match_request__to_profile__user=user)
    )


def filter_messages_for_user(qs, user):
    """
    Foydalanuvchi o'qiy oladigan xabarlarni filtrlaydi.

    Faqat o'zi ishtirok etayotgan chat xonalaridagi xabarlar ko'rinadi.

    :param qs: Asosiy xabarlar QuerySet-i.
    :param user: So'rov yuborayotgan foydalanuvchi (User).
    :return: Filtrlangan QuerySet.
    """
    if not user or not user.is_authenticated:
        return qs.none()

    if _is_staff_user(user):
        return qs

    return qs.filter(
        Q(chat_room__match_request__from_profile__user=user)
        | Q(chat_room__match_request__to_profile__user=user)
    )


def mark_room_messages_read(chat_room, user):
    """
    Xonadagi, foydalanuvchi o'zi yozmagan o'qilmagan xabarlarni o'qilgan deb belgilaydi.

    :param chat_room: Chat xonasi (ChatRoom).
    :param user: O'qidi deb belgilayotgan foydalanuvchi (User).
    :return: Yangilangan xabarlar soni (int).
    """
    return (
        Message.objects.active()
        .filter(chat_room=chat_room, is_read=False)
        .exclude(sender=user)
        .update(is_read=True)
    )


def count_unread_messages(user, chat_room=None):
    """
    Foydalanuvchi uchun o'qilmagan xabarlar sonini qaytaradi.

    Xonaning boshqa ishtirokchisi yuborgan, `is_read=False` xabarlar sanaladi.

    :param user: Foydalanuvchi (User).
    :param chat_room: Berilsa, faqat shu xona bo'yicha sanaydi (ChatRoom | None).
    :return: O'qilmagan xabarlar soni (int).
    """
    qs = Message.objects.active().filter(is_read=False).exclude(sender=user)
    qs = filter_messages_for_user(qs, user)
    if chat_room is not None:
        qs = qs.filter(chat_room=chat_room)
    return qs.count()


def build_message_payload(message):
    """
    Xabarni WebSocket orqali yuborish uchun oddiy dict ko'rinishiga keltiradi.

    :param message: Xabar (Message).
    :return: Serializatsiya qilingan xabar (dict).
    """
    reply = message.reply_to
    reply_payload = None
    if reply is not None:
        reply_payload = {
            "id": str(reply.id),
            "sender": str(reply.sender_id),
            "content": reply.content,
            "attachment": reply.attachment.url if reply.attachment else None,
        }
    return {
        "id": str(message.id),
        "chat_room": str(message.chat_room_id),
        "sender": str(message.sender_id),
        "content": message.content,
        "attachment": message.attachment.url if message.attachment else None,
        "reply_to": reply_payload,
        "is_read": message.is_read,
        "created_at": (message.created_at.isoformat() if message.created_at else ""),
    }


def broadcast_new_message(message):
    """
    Yangi xabarni chat xonasi WebSocket guruhiga jonli yuboradi.

    Channel layer ishlamay qolsa ham xabar yaratish (REST) buzilmasligi uchun
    xatolik yutiladi va logga yoziladi.

    :param message: Yuborilgan xabar (Message).
    :return: None
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            f"chat_{message.chat_room_id}",
            {"type": "chat_message", "message": build_message_payload(message)},
        )
    except Exception:
        logger.exception(
            "Chat xabarini WebSocket'ga yuborib bo'lmadi: message_id=%s", message.id
        )


def notify_recipient_new_message(message):
    """
    Xabar qabul qiluvchiga bildirishnoma yozadi (push/WebSocket zanjirini ishga soladi).

    Qabul qiluvchi — xonaning sender bo'lmagan ikkinchi ishtirokchisi.

    :param message: Yuborilgan xabar (Message). Yuboruvchi `message.sender`.
    :return: None
    """
    sender = message.sender
    chat_room = message.chat_room
    if not chat_room or not chat_room.match_request:
        return

    mr = chat_room.match_request
    recipient_user = None
    if mr.from_profile and mr.from_profile.user_id != sender.id:
        recipient_user = mr.from_profile.user
    elif mr.to_profile and mr.to_profile.user_id != sender.id:
        recipient_user = mr.to_profile.user

    if not recipient_user:
        return

    from apps.accounts.notifications.models import Notification

    sender_name = getattr(
        getattr(sender, "profile", None), "first_name", "Foydalanuvchi"
    )
    preview = message.content[:100] or "📎 Biriktirilgan fayl"
    Notification.objects.create(
        user=recipient_user,
        title=f"{sender_name}dan yangi xabar",
        message=preview,
        extra_data={
            "type": "new_chat_message",
            "chat_room_id": str(chat_room.id),
            "sender_id": str(sender.id),
        },
    )


def persist_chat_message(chat_room, sender, content, reply_to_id=None):
    """
    Chat xabarini bazaga yozadi va qabul qiluvchiga bildirishnoma yaratadi.

    WebSocket consumer'idan chaqiriladi (jonli tarqatish alohida bajariladi).
    REST yo'li serializer orqali saqlaydi, keyin shu bildirishnoma qismini
    `notify_recipient_new_message` bilan qo'zg'atadi.

    :param chat_room: Chat xonasi (ChatRoom).
    :param sender: Yuboruvchi (User).
    :param content: Xabar matni (str).
    :param reply_to_id: Javob berilayotgan xabar ID si (str | None).
    :raises ValueError: reply_to xabari topilmasa yoki boshqa xonaga tegishli bo'lsa.
    :return: Yaratilgan xabar (Message).
    """
    reply_to = None
    if reply_to_id:
        reply_to = (
            Message.objects.active().filter(pk=reply_to_id, chat_room=chat_room).first()
        )
        if reply_to is None:
            raise ValueError(
                "Javob berilayotgan xabar topilmadi yoki boshqa chat xonasiga tegishli."
            )

    message = Message.objects.create(
        chat_room=chat_room, sender=sender, content=content, reply_to=reply_to
    )
    notify_recipient_new_message(message)
    return message
