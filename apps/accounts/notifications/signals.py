import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .tasks import mass_notification_sender
from .models import Notification

logger = logging.getLogger(__name__)


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
    if created:
        message_data = {
            "user_id": str(instance.user.id),
            "notification_id": str(instance.id),
            "title": instance.title,
            "message": instance.message,
            "extra_data": instance.extra_data or {},
            "schema_version": "1",
            "created_at": instance.created_at.isoformat()
            if instance.created_at
            else "",
        }

        transaction.on_commit(lambda: enqueue_notification(message_data))
