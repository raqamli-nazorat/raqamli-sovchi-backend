from django.db.models import Q


def is_female_candidate(profile):
    if not profile:
        return False

    if profile.gender == "female" or profile.candidate_type == "bride":
        return True

    if profile.representative_infos.filter(candidate_role="bride").exists():
        return True

    return False


def can_view_profile_photos(request_user, target_profile):
    """
    Foydalanuvchi nishon profilning rasmlarini ko'ra olish-olmasligini aniqlaydi.

    Ikki profil orasida holati PENDING yoki ACCEPTED bo'lgan MatchRequest bo'lsa
    (qaysi tomon yuborgani muhim emas) rasm ochiq hisoblanadi — jinsidan qat'iy
    nazar. So'rov REJECTED bo'lsa (yoki umuman bo'lmasa) rasm yana yopiladi;
    bu holat hech qayerda saqlanmaydi, har chaqiriqda jonli hisoblanadi.
    Faol so'rov bo'lmasa: qiz nomzod uchun har doim yopiq, boshqalar uchun
    `blur_photos` bayrog'iga qarab belgilanadi.

    :param request_user: So'rov yuborayotgan foydalanuvchi (User).
    :param target_profile: Rasmlari tekshirilayotgan profil (Profile).
    :return: Ko'rish huquqi bo'lsa True, aks holda False (bool).
    """
    if not request_user or not request_user.is_authenticated:
        return False

    if not target_profile:
        return False

    if target_profile.user_id == request_user.id:
        return True

    is_admin_role = (
        getattr(request_user, "is_superuser", False)
        or getattr(request_user, "is_staff", False)
        or bool(request_user.role and not request_user.role.is_default)
    )
    if is_admin_role:
        return False

    from apps.matches.match_requests.models import MatchRequest, MatchRequestStatus

    user_profile = getattr(request_user, "profile", None)

    has_active_match = False
    if user_profile:
        has_active_match = (
            MatchRequest.objects.active()
            .filter(
                status__in=[MatchRequestStatus.PENDING, MatchRequestStatus.ACCEPTED]
            )
            .filter(
                Q(from_profile=user_profile, to_profile=target_profile)
                | Q(from_profile=target_profile, to_profile=user_profile)
            )
            .exists()
        )

    if has_active_match:
        return True

    if is_female_candidate(target_profile):
        return False

    if not target_profile.blur_photos:
        return True

    return False
