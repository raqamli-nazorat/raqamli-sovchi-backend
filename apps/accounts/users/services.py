import logging
from apps.accounts.users.models import UserDevice

logger = logging.getLogger(__name__)


def register_or_update_user_device(user, request):
    if not request or not user or not user.is_authenticated:
        return None

    device_id = request.headers.get("X-Device-Id") or request.META.get("HTTP_X_DEVICE_ID")
    if not device_id:
        return None

    device_name = request.headers.get("X-Device-Name") or request.META.get("HTTP_X_DEVICE_NAME")
    device_os = request.headers.get("X-Device-OS") or request.META.get("HTTP_X_DEVICE_OS")

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.META.get("REMOTE_ADDR")

    device, created = UserDevice.objects.update_or_create(
        user=user,
        device_id=device_id,
        defaults={
            "device_name": device_name,
            "device_os": device_os,
            "ip_address": ip_address,
            "is_active": True,
        },
    )

    if created:
        logger.info("Yangi qurilma ro'yxatga olindi: UserID=%s | DeviceID=%s | Name=%s", user.id, device_id, device_name)
    else:
        logger.debug("Qurilma ma'lumoti yangilandi: UserID=%s | DeviceID=%s", user.id, device_id)

    return device
