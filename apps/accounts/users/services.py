import logging
from django.core.cache import cache
from apps.accounts.users.models import UserDevice

logger = logging.getLogger(__name__)

DEVICE_CACHE_TIMEOUT = 30 * 24 * 3600  # 30 kun


def get_device_cache_key(user_id, device_id):
    return f"user:{user_id}:device:{device_id}:active"


def set_device_active_in_redis(user_id, device_id, is_active=True):
    key = get_device_cache_key(user_id, device_id)
    try:
        cache.set(key, is_active, timeout=DEVICE_CACHE_TIMEOUT)
    except Exception as e:
        logger.warning("Redis ga qurilma holatini yozishda xatolik: %s", e)


def is_device_active_in_redis(user_id, device_id):
    if not user_id or not device_id:
        return True

    key = get_device_cache_key(user_id, device_id)
    try:
        val = cache.get(key)
        if val is not None:
            return bool(val)
    except Exception as e:
        logger.warning("Redis dan qurilma holatini o'qishda xatolik: %s", e)

    is_active = UserDevice.objects.filter(
        user_id=user_id, device_id=device_id, is_active=True
    ).exists()

    set_device_active_in_redis(user_id, device_id, is_active)
    return is_active


def revoke_device_in_redis(user_id, device_id):
    set_device_active_in_redis(user_id, device_id, is_active=False)


def revoke_all_other_devices(user, current_device_id):
    qs = UserDevice.objects.filter(user=user, is_active=True)
    if current_device_id:
        qs = qs.exclude(device_id=current_device_id)

    revoked_devices = list(qs.values_list("device_id", flat=True))
    count = qs.update(is_active=False)

    for dev_id in revoked_devices:
        revoke_device_in_redis(user.id, dev_id)

    return count


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
            "ip_address": ip_address
        },
    )

    set_device_active_in_redis(user.id, device_id, is_active=True)

    if created:
        logger.info("Yangi qurilma ro'yxatga olindi: UserID=%s | DeviceID=%s | Name=%s", user.id, device_id, device_name)
    else:
        logger.debug("Qurilma ma'lumoti yangilandi: UserID=%s | DeviceID=%s", user.id, device_id)

    return device
