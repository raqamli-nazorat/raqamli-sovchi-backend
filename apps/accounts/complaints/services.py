from apps.accounts.complaints.models import Complaint, ComplaintStatus


def is_staff_like(user):
    """
    Foydalanuvchi moderator/xodim toifasiga kirishini tekshiradi.

    :param user: Foydalanuvchi.
    :return: Xodim bo'lsa True, aks holda False.
    """
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_staff
            or user.is_superuser
            or (getattr(user, "role", None) and not user.role.is_default)
        )
    )


def filter_complaints_for_user(queryset, user):
    """
    Foydalanuvchiga ko'rinishi kerak bo'lgan shikoyatlarni qaytaradi.

    Oddiy foydalanuvchi faqat o'zi yuborgan shikoyatlarni ko'radi.
    Xodim/moderator esa barcha shikoyatlarni ko'radi.

    :param queryset: Complaint queryset.
    :param user: Foydalanuvchi.
    :return: Filtrlangan queryset.
    """
    if not user or not user.is_authenticated:
        return queryset.none()

    if is_staff_like(user):
        return queryset

    return queryset.filter(from_user=user)


def get_profile_completion_percentage(user):
    """
    Foydalanuvchi anketasining taxminiy to'liqlik foizini hisoblaydi.

    :param user: Foydalanuvchi.
    :return: 0 dan 100 gacha foiz.
    """
    profile = getattr(user, "profile", None)
    if not profile:
        return 0

    score = 0
    if profile.first_name:
        score += 10
    if profile.last_name:
        score += 10
    if profile.gender:
        score += 10
    if profile.candidate_type:
        score += 10
    if profile.birth_date:
        score += 10
    if profile.height and profile.weight:
        score += 10
    if profile.region:
        score += 10
    if profile.district:
        score += 10
    if profile.marital_status:
        score += 10
    if profile.pk and hasattr(profile, "photos") and bool(profile.photos.all()):
        score += 10
    return score


def get_user_status_label(user):
    """
    Foydalanuvchining qisqa holat matnini qaytaradi.

    :param user: Foydalanuvchi.
    :return: Holat matni.
    """
    if user.is_blocked:
        return "Bloklangan"
    if get_profile_completion_percentage(user) < 50:
        return "Anketa to'liq emas"
    if not user.is_verified:
        return "Tekshiruvda"
    return "Tasdiqlangan"


def build_profile_snapshot(user):
    """
    Shikoyat detail sahifasi uchun profil snapshotini tayyorlaydi.

    :param user: Shikoyat qilingan foydalanuvchi.
    :return: Lug'at ko'rinishidagi snapshot.
    """
    profile = getattr(user, "profile", None)
    ai_signals_count = Complaint.objects.active().filter(
        to_user=user, status=ComplaintStatus.APPROVED
    ).count()
    return {
        "status": get_user_status_label(user),
        "joined_at": user.created_at,
        "completion_percentage": get_profile_completion_percentage(user),
        "ai_signals_count": ai_signals_count,
        "is_blocked": user.is_blocked,
        "profile_id": str(profile.id) if profile else None,
    }


def build_ai_analysis(complaint):
    """
    Detail sahifa uchun soddalashtirilgan tahlil ma'lumotini qaytaradi.

    :param complaint: Shikoyat obyektı.
    :return: Tahlil natijasi lug'ati.
    """
    previous_count = Complaint.objects.active().filter(to_user=complaint.to_user).exclude(
        pk=complaint.pk
    ).count()
    recommendation = (
        "Profilni bloklash" if previous_count >= 3 else "Qo'shimcha tekshiruv"
    )
    risk_level = "Yuqori" if previous_count >= 3 else "O'rta"
    return {
        "risk_level": risk_level,
        "previous_warnings_count": previous_count,
        "complaints_count": previous_count,
        "recommended_action": recommendation,
    }
