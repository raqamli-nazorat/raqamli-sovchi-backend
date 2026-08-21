import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any

from celery import shared_task, group
from firebase_admin import messaging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import UserDevice

logger = logging.getLogger(__name__)

FCM_BATCH_SIZE = 500


@dataclass(frozen=True, slots=True)
class NotificationPayload:
    user_id: str
    notification_id: str
    title: str
    message: str
    extra_data: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1"
    created_at: str = ""

    def __post_init__(self):
        missing = [f for f in ("user_id", "title", "message") if not getattr(self, f)]
        if missing:
            raise ValueError(f"Majburiy maydonlar yo'q: {missing}")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(
            user_id=str(data["user_id"]),
            notification_id=str(data.get("notification_id") or data.get("id") or ""),
            title=data.get("title") or "Xabarnoma",
            message=data.get("message") or "",
            extra_data=data.get("extra_data") or {},
            schema_version=str(data.get("schema_version") or "1"),
            created_at=str(data.get("created_at") or ""),
        )


@shared_task
def mass_notification_sender(raw_list):
    if not raw_list:
        return "Ro'yxat bo'sh"

    valid, skipped = [], 0
    for raw in raw_list:
        try:
            valid.append(
                send_single_notification_task.s(
                    NotificationPayload.from_dict(raw).to_dict()
                )
            )
        except Exception as e:
            logger.warning("Noto'g'ri payload o'tkazib yuborildi: %s", type(e).__name__)
            skipped += 1

    if not valid:
        return "Barcha yozuvlar noto'g'ri."

    group(valid).apply_async()
    return f"{len(valid)} ta yuborildi" + (
        f", {skipped} ta o'tkazib yuborildi." if skipped else "."
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def send_single_notification_task(self, raw):
    try:
        p = NotificationPayload.from_dict(raw)
    except Exception as e:
        raise self.retry(exc=e, max_retries=0)

    group(
        send_websocket_notification.s(p.to_dict()),
        send_push_notification_task.s(
            user_id=p.user_id,
            notification_id=p.notification_id,
            title=p.title,
            message=p.message,
            extra_data=p.extra_data,
            schema_version=p.schema_version,
        ),
    ).apply_async()
    return "WebSocket va Push tasklari guruhlanib yuborildi."


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def send_websocket_notification(self, data):
    channel_layer = get_channel_layer()
    if not channel_layer:
        raise RuntimeError("Channel layer mavjud emas.")

    async_to_sync(channel_layer.group_send)(
        f"user_{data['user_id']}_notifications",
        {"type": "send_notification", "message": data},
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def send_push_notification_task(
    self,
    user_id,
    notification_id="",
    title="",
    message="",
    extra_data=None,
    schema_version="1",
):
    tokens = list(
        UserDevice.objects.active()
        .filter(user_id=user_id)
        .exclude(fcm_token__isnull=True)
        .exclude(fcm_token="")
        .values_list("fcm_token", flat=True)
    )

    if not tokens:
        return "Foydalanuvchi uchun faol tokenlar topilmadi."

    fcm_data = {
        "notification_id": str(notification_id or ""),
        "title": title or "",
        "message": message or "",
        "payload": json.dumps(extra_data or {}),
        "schema_version": str(schema_version or "1"),
    }

    success = failure = 0
    invalid_tokens = []

    for i in range(0, len(tokens), FCM_BATCH_SIZE):
        batch = tokens[i : i + FCM_BATCH_SIZE]
        response = messaging.send_each_for_multicast(
            messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title or "Xabarnoma",
                    body=message or "",
                ),
                data=fcm_data,
                tokens=batch,
            )
        )
        success += response.success_count
        failure += response.failure_count
        invalid_tokens += [
            batch[j]
            for j, r in enumerate(response.responses)
            if not r.success
            and isinstance(
                r.exception,
                (messaging.UnregisteredError, messaging.SenderIdMismatchError),
            )
        ]

    if invalid_tokens:
        UserDevice.objects.filter(fcm_token__in=invalid_tokens).delete()
        logger.warning("FCM: %d ta eskirgan token tozalandi.", len(invalid_tokens))

    logger.info("FCM jo'natish yakunlandi: ok=%d | fail=%d", success, failure)
    return f"FCM: {success} muvaffaqiyatli, {failure} muvaffaqiyatsiz"
