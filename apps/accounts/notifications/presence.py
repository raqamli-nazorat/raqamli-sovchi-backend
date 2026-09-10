"""Foydalanuvchining onlayn holatini Redis (kesh) orqali kuzatadi.

Har WebSocket ulanish `presence:conn:{user_id}` sanog'ini oshiradi, ulanish
uzilganda kamaytiradi. Sanoq 0 dan 1 ga o'tsa foydalanuvchi "online" bo'ldi,
1 dan 0 ga tushsa "offline" bo'ldi deb hisoblanadi. Kalitga qisqa TTL qo'yiladi:
mijoz vaqtida `ping` yubormay qo'ysa (masalan internet uzilsa), kalit o'zi
eskiradi va foydalanuvchi offline holatga o'tadi.

Bir foydalanuvchi bir nechta qurilmadan ulanishi mumkin — shuning uchun oddiy
flag emas, sanoq ishlatiladi.
"""

import logging

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

# Mijoz ~30 soniyada bir marta `ping` yuborishi kutiladi; TTL undan biroz katta.
PRESENCE_TTL = 70
# "Oxirgi ko'rilgan" vaqti keshda shuncha saqlanadi.
LAST_SEEN_TTL = 60 * 60 * 24 * 30


def _conn_key(user_id):
    """Ulanishlar sanog'i uchun kesh kaliti."""
    return f"presence:conn:{user_id}"


def _last_seen_key(user_id):
    """Oxirgi faollik vaqti uchun kesh kaliti."""
    return f"presence:last_seen:{user_id}"


def mark_online(user_id):
    """Ulanish sanog'ini oshiradi.

    :param user_id: Foydalanuvchi ID si.
    :return: Foydalanuvchi endigina onlayn bo'lsa True (bool).
    """
    key = _conn_key(str(user_id))
    try:
        count = cache.incr(key, ignore_key_check=True)
    except Exception:
        logger.exception("presence.mark_online xatosi: user_id=%s", user_id)
        return False
    cache.expire(key, PRESENCE_TTL)
    return count == 1


def touch(user_id):
    """`ping` kelganda kalit TTL sini uzaytiradi.

    Kalit eskirib ketgan bo'lsa (lekin ulanish hali tirik) — qayta tiklaydi.

    :param user_id: Foydalanuvchi ID si.
    :return: Kalit eskirgan bo'lib qayta tiklangan bo'lsa True (bool).
    """
    key = _conn_key(str(user_id))
    if cache.get(key) is None:
        cache.set(key, 1, timeout=PRESENCE_TTL)
        return True
    cache.expire(key, PRESENCE_TTL)
    return False


def mark_offline(user_id):
    """Ulanish sanog'ini kamaytiradi.

    :param user_id: Foydalanuvchi ID si.
    :return: (endigina offline bo'ldimi, last_seen ISO vaqti | None) (tuple).
    """
    key = _conn_key(str(user_id))
    try:
        count = cache.decr(key)
    except ValueError:
        count = 0
    except Exception:
        logger.exception("presence.mark_offline xatosi: user_id=%s", user_id)
        return False, None

    if count > 0:
        cache.expire(key, PRESENCE_TTL)
        return False, None

    cache.delete(key)
    last_seen = timezone.now().isoformat()
    cache.set(_last_seen_key(str(user_id)), last_seen, timeout=LAST_SEEN_TTL)
    return True, last_seen


def get_presence(user_id):
    """Foydalanuvchining hozirgi holatini qaytaradi.

    :param user_id: Foydalanuvchi ID si.
    :return: {"user", "status": "online"|"offline", "last_seen"} (dict).
    """
    user_id = str(user_id)
    if cache.get(_conn_key(user_id)):
        return {"user": user_id, "status": "online", "last_seen": None}
    return {
        "user": user_id,
        "status": "offline",
        "last_seen": cache.get(_last_seen_key(user_id)),
    }


def get_chat_partner_ids(user_id):
    """Foydalanuvchi bilan faol chat xonasi bor bo'lganlarning ID to'plami.

    Holat o'zgarishi faqat shu odamlarga tarqatiladi (hammaga emas).

    :param user_id: Foydalanuvchi ID si.
    :return: Suhbatdoshlar ID lari to'plami (set[str]).
    """
    from apps.matches.chats.models import ChatRoom

    user_id = str(user_id)
    pairs = (
        ChatRoom.objects.active()
        .filter(
            Q(match_request__from_profile__user_id=user_id)
            | Q(match_request__to_profile__user_id=user_id)
        )
        .values_list(
            "match_request__from_profile__user_id",
            "match_request__to_profile__user_id",
        )
    )
    partners = set()
    for from_id, to_id in pairs:
        for pid in (from_id, to_id):
            if pid is not None and str(pid) != user_id:
                partners.add(str(pid))
    return partners
