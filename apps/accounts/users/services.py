import logging
from django.core.cache import cache
from apps.accounts.users.models import UserDevice

logger = logging.getLogger(__name__)

DEVICE_CACHE_TIMEOUT = 30 * 24 * 3600


def get_device_cache_key(user_id, device_id):
    """
    Foydalanuvchi qurilmasining Redis kech kalitini shakllantiradi.

    :param user_id: Foydalanuvchi ID si (UUID yoki int).
    :param device_id: Qurilma identifikatori (string).
    :return: Redis kech kaliti (string).
    """
    return f"user:{user_id}:device:{device_id}:active"


def set_device_active_in_redis(user_id, device_id, is_active=True):
    """
    Qurilmaning faollik holatini Redis keshiga yozadi.

    :param user_id: Foydalanuvchi ID si.
    :param device_id: Qurilma identifikatori.
    :param is_active: Qurilma faollik holati (bool, default=True).
    :return: None
    """
    key = get_device_cache_key(user_id, device_id)
    try:
        cache.set(key, is_active, timeout=DEVICE_CACHE_TIMEOUT)
    except Exception as e:
        logger.warning("Redis ga qurilma holatini yozishda xatolik: %s", e)


def is_device_active_in_redis(user_id, device_id):
    """
    Qurilmaning faolligini avval Redis kechidan, topilmasa ma'lumotlar bazasidan tekshiradi.

    :param user_id: Foydalanuvchi ID si.
    :param device_id: Qurilma identifikatori.
    :return: Qurilma faol bo'lsa True, aks holda False (bool).
    """
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
    """
    Qurilmaning faollik holatini Redis kechida bekor qiladi (False qilib yozadi).

    :param user_id: Foydalanuvchi ID si.
    :param device_id: Qurilma identifikatori.
    :return: None
    """
    set_device_active_in_redis(user_id, device_id, is_active=False)


def revoke_all_other_devices(user, current_device_id):
    """
    Foydalanuvchining joriy qurilmasidan tashqari barcha boshqa faol qurilmalarini bekor qiladi (deaktivatsiyalaydi).

    :param user: Foydalanuvchi obyekti (User).
    :param current_device_id: Saqlanib qoladigan joriy qurilma ID si.
    :return: Bekor qilingan qurilmalar soni (int).
    """
    qs = UserDevice.objects.filter(user=user, is_active=True)
    if current_device_id:
        qs = qs.exclude(device_id=current_device_id)

    revoked_devices = list(qs.values_list("device_id", flat=True))
    count = qs.update(is_active=False)

    for dev_id in revoked_devices:
        revoke_device_in_redis(user.id, dev_id)

    return count


def register_or_update_user_device(user, request):
    """
    HTTP so'rov sarlavhalaridan (X-Device-Id, X-Device-Name, X-Device-OS) foydalanib
    foydalanuvchi qurilmasini ro'yxatdan o'tkazadi yoki yangilaydi.

    :param user: Foydalanuvchi obyekti (User).
    :param request: HTTP Request obyekti.
    :return: Yaratilgan yoki yangilangan UserDevice obyekti yoki None.
    """
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
    """
    Nofaol (deaktivatsiyalangan) foydalanuvchini qayta faollashtiradi va uning eski ma'lumotlarini tozalaydi.

    :param user: Foydalanuvchi obyekti (User).
    :param new_auth_provider: Yangi autentifikatsiya provayderi (masalan, 'google', 'phone', 'email').
    :return: None
    """
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
    """
    Google OAuth ID Token orqali foydalanuvchini autentifikatsiya qiladi yoki yangi hisob yaratadi.

    :param id_token_str: Google yuborgan ID token matni.
    :param request: HTTP Request obyekti.
    :return: (user, tokens, is_blocked) uchtaligi.
    :raises ValidationError: Token yaroqsiz bo'lganda.
    """
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
    """
    Telefon raqami orqali foydalanuvchini autentifikatsiya qiladi yoki yangi hisob yaratadi va JWT belgilarni (tokens) qaytaradi.

    :param phone_number: Foydalanuvchi telefon raqami (masalan "+998901234567").
    :param request: HTTP Request obyekti.
    :return: (user, tokens, is_blocked) uchtaligi.
    """
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
    """
    Email manzili orqali foydalanuvchini autentifikatsiya qiladi yoki yangi hisob yaratadi va JWT belgilarni (tokens) qaytaradi.

    :param email: Foydalanuvchi email manzili.
    :param request: HTTP Request obyekti.
    :return: (user, tokens, is_blocked) uchtaligi.
    """
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
