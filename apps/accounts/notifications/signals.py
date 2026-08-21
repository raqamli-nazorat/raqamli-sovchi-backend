from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .tasks import mass_notification_sender
from .models import Notification


@receiver(post_save, sender=Notification)
def post_save_handler(sender, instance, created, **kwargs):
    if created:
        message_data = {
            "id": str(instance.id),
            "user_id": str(instance.user.id),
            "id": str(instance.id),
            "title": instance.title,
            "message": instance.message,
            "extra_data": instance.extra_data or {},
            "created_at": instance.created_at.isoformat(),
        }

        transaction.on_commit(lambda: mass_notification_sender.delay([message_data]))
