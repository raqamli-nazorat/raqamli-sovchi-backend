import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.users.models import User

from .models import (
    NOTIFICATION_TYPE_PREFERENCE_FIELDS,
    Notification,
    NotificationPreference,
)
from .tasks import mass_notification_sender

logger = logging.getLogger(__name__)


def is_notification_type_enabled(user_id, notification_type):
    """
    Foydalanuvchi shu turdagi bildirishnomani (push/WebSocket) yoqqanmi tekshiradi.

    Sozlama yozuvi hali yaratilmagan bo'lsa yoki tur preferensiyaga bog'liq
    bo'lmasa — yoqilgan deb hisoblanadi (default xatti-harakat).

    :param user_id: Qabul qiluvchi foydalanuvchi ID si.
    :param notification_type: `NotificationType` qiymati.
    :return: bool.
    """
    field_name = NOTIFICATION_TYPE_PREFERENCE_FIELDS.get(notification_type)
    if not field_name:
        return True

    preference = (
        NotificationPreference.objects.filter(user_id=user_id).only(field_name).first()
    )
    if not preference:
        return True

    return getattr(preference, field_name)


@receiver(post_save, sender=User)
def create_notification_preference(sender, instance, created, **kwargs):
    if created:
        NotificationPreference.objects.get_or_create(user=instance)


def enqueue_notification(message_data):
    """
    Xabarnomani Celery navbatiga qo'yadi.

    Broker ishlamay qolsa ham asosiy amaliyot (masalan, moslik so'rovi
    yaratish) yiqilmasligi uchun xatolik yutiladi va logga yoziladi.

    :param message_data: Xabarnoma ma'lumotlari (dict).
    :return: None
    """
    try:
        mass_notification_sender.delay([message_data])
    except Exception:
        logger.exception(
            "Xabarnomani navbatga qo'shib bo'lmadi: notification_id=%s",
            message_data.get("notification_id"),
        )


@receiver(post_save, sender=Notification)
def post_save_handler(sender, instance, created, **kwargs):
    if not created:
        return

    if not is_notification_type_enabled(instance.user_id, instance.type):
        return

    message_data = {
        "user_id": str(instance.user.id),
        "notification_id": str(instance.id),
        "title": instance.title,
        "message": instance.message,
        "extra_data": instance.extra_data or {},
        "schema_version": "1",
        "created_at": (instance.created_at.isoformat() if instance.created_at else ""),
    }

    transaction.on_commit(lambda: enqueue_notification(message_data))
