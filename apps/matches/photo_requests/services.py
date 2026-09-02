from django.db.models import Q

from apps.accounts.profiles.models import RepresentativeInfo


def filter_photo_requests_for_user(qs, user):
    """
    Foydalanuvchi ko'rishi mumkin bo'lgan rasm so'rovlarini filtrlaydi.

    Oddiy foydalanuvchi faqat o'zi yuborgan yoki o'ziga kelgan so'rovlarni ko'radi.
    Vakil bo'lsa, vakillik qilayotgan nomzodlarga kelgan so'rovlar ham qo'shiladi.
    Xodim rolidagilar barcha so'rovlarni ko'radi.

    :param qs: Asosiy rasm so'rovlari QuerySet-i.
    :param user: So'rov yuborayotgan foydalanuvchi (User).
    :return: Filtrlangan QuerySet.
    """
    if not user or not user.is_authenticated:
        return qs.none()

    if (
        user.is_staff
        or user.is_superuser
        or bool(user.role and not user.role.is_default)
    ):
        return qs

    profile = getattr(user, "profile", None)
    if not profile:
        return qs.none()

    represented_user_ids = RepresentativeInfo.objects.filter(
        profile=profile,
        is_approved=True,
        target_candidate__isnull=False,
    ).values_list("target_candidate_id", flat=True)

    return qs.filter(
        Q(from_profile=profile)
        | Q(to_profile=profile)
        | Q(to_profile__user_id__in=represented_user_ids)
    )


def can_decide_photo_request(user, photo_request):
    """
    Foydalanuvchi ushbu so'rovni qabul qilish yoki rad etish huquqiga egaligini tekshiradi.

    Qaror qabul qiluvchi nomzodning o'zi yoki uning tasdiqlangan vakili bo'lishi mumkin.

    :param user: So'rov yuborayotgan foydalanuvchi (User).
    :param photo_request: Rasm ko'rish so'rovi (PhotoRequest).
    :return: Huquqi bo'lsa True, aks holda False (bool).
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    profile = getattr(user, "profile", None)
    if not profile:
        return False

    if profile == photo_request.to_profile:
        return True

    rep_info = (
        RepresentativeInfo.objects.select_related("profile__user")
        .filter(
            target_candidate_id=photo_request.to_profile.user_id,
            is_approved=True,
        )
        .first()
    )

    if not rep_info or not rep_info.profile:
        return False

    return rep_info.profile.user_id == user.id
