import logging
from django.core.cache import cache
from apps.accounts.users.models import UserDevice

logger = logging.getLogger(__name__)

DEVICE_CACHE_TIMEOUT = 30 * 24 * 3600


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

    device_id = request.headers.get("X-Device-Id") or request.META.get(
        "HTTP_X_DEVICE_ID"
    )
    if not device_id:
        return None

    device_name = request.headers.get("X-Device-Name") or request.META.get(
        "HTTP_X_DEVICE_NAME"
    )
    device_os = request.headers.get("X-Device-OS") or request.META.get(
        "HTTP_X_DEVICE_OS"
    )

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
        },
    )

    set_device_active_in_redis(user.id, device_id, is_active=True)

    if created:
        logger.info(
            "Yangi qurilma ro'yxatga olindi: UserID=%s | DeviceID=%s | Name=%s",
            user.id,
            device_id,
            device_name,
        )
    return device


def _reactivate_user_if_needed(user, new_auth_provider=None):
    if not user or user.is_active:
        return

    user.is_active = True
    if new_auth_provider:
        user.auth_provider = new_auth_provider
    user.save(update_fields=["is_active", "auth_provider", "updated_at"])

    profile = getattr(user, "profile", None)
    if profile:
        profile.hard_delete()

    from apps.accounts.users.models import UserDevice, UserPledge
    from apps.accounts.notifications.models import Notification
    from allauth.socialaccount.models import SocialAccount

    UserDevice.objects.filter(user=user).delete()
    UserPledge.objects.filter(user=user).delete()
    Notification.objects.filter(user=user).delete()
    SocialAccount.objects.filter(user=user).delete()


def authenticate_google_user(id_token_str, request):
    import requests as http_requests
    from allauth.socialaccount.models import SocialAccount
    from rest_framework.exceptions import ValidationError
    from apps.accounts.users.models import User, AuthProvider
    from apps.accounts.users.utils import get_tokens_for_user

    resp = http_requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": id_token_str},
        timeout=10,
    )
    if resp.status_code != 200 or "error" in resp.json():
        raise ValidationError("Google ID token yaroqsiz yoki muddati o'tgan.")

    user_info = resp.json()
    google_uid = user_info.get("sub")
    email = (user_info.get("email") or "").lower().strip()

    if not google_uid:
        raise ValidationError("Google foydalanuvchi ma'lumotlarini olishda xatolik.")

    social_acc = SocialAccount.objects.filter(provider="google", uid=google_uid).first()

    if social_acc:
        user = social_acc.user
        created = False
    else:
        user = User.objects.filter(email=email).first() if email else None
        if user:
            created = False
        else:
            user = User.objects.create(
                email=email or None,
                auth_provider=AuthProvider.GOOGLE,
                is_verified=True,
            )
            created = True

    _reactivate_user_if_needed(user)

    if not created and user.is_blocked:
        return None, None, True

    update_fields = []
    if not user.email and email:
        user.email = email
        update_fields.append("email")
    if not created and user.auth_provider != AuthProvider.GOOGLE:
        user.auth_provider = AuthProvider.GOOGLE
        update_fields.append("auth_provider")
    if update_fields:
        user.save(update_fields=update_fields)

    if not social_acc:
        SocialAccount.objects.get_or_create(
            provider="google",
            uid=google_uid,
            defaults={"user": user, "extra_data": user_info},
        )

    device = register_or_update_user_device(user, request)
    device_id = device.device_id if device else request.headers.get("X-Device-Id")
    tokens = get_tokens_for_user(user, device_id=device_id)

    return user, tokens, False


def authenticate_phone_user(phone_number, request):
    from apps.accounts.users.models import User, AuthProvider
    from apps.accounts.users.utils import get_tokens_for_user

    user = User.objects.filter(phone_number=phone_number).first()

    if not user:
        user = User.objects.create(
            phone_number=phone_number,
            auth_provider=AuthProvider.PHONE,
        )
        created = True
    else:
        created = False
        _reactivate_user_if_needed(user)

    if not created and user.is_blocked:
        return None, None, True

    if not created and user.auth_provider != AuthProvider.PHONE:
        user.auth_provider = AuthProvider.PHONE
        user.save(update_fields=["auth_provider"])

    device = register_or_update_user_device(user, request)
    device_id = device.device_id if device else request.headers.get("X-Device-Id")
    tokens = get_tokens_for_user(user, device_id=device_id)

    return user, tokens, False


def authenticate_email_user(email, request):
    from apps.accounts.users.models import User, AuthProvider
    from apps.accounts.users.utils import get_tokens_for_user

    email_clean = email.lower()
    user = User.objects.filter(email=email_clean).first()

    if not user:
        user = User.objects.create(
            email=email_clean,
            auth_provider=AuthProvider.EMAIL,
        )
        created = True
    else:
        created = False
        _reactivate_user_if_needed(user)

    if not created and user.is_blocked:
        return None, None, True

    if not created and user.auth_provider != AuthProvider.EMAIL:
        user.auth_provider = AuthProvider.EMAIL
        user.save(update_fields=["auth_provider"])

    device = register_or_update_user_device(user, request)
    device_id = device.device_id if device else request.headers.get("X-Device-Id")
    tokens = get_tokens_for_user(user, device_id=device_id)

    return user, tokens, False
