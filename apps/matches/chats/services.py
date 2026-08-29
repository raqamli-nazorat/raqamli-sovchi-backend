from django.db.models import Q


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
