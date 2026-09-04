from apps.accounts.complaints.models import (
    Complaint,
    ComplaintEnforcementAction,
    ComplaintStatus,
)


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
    ai_signals_count = (
        Complaint.objects.active()
        .filter(to_user=user, status=ComplaintStatus.APPROVED)
        .count()
    )
    return {
        "status": get_user_status_label(user),
        "joined_at": user.created_at,
        "completion_percentage": get_profile_completion_percentage(user),
        "questionnaire_progress": get_questionnaire_progress(user),
        "ai_signals_count": ai_signals_count,
        "is_blocked": user.is_blocked,
        "profile_id": str(profile.id) if profile else None,
    }


def build_ai_analysis(complaint):
    """
    Detail sahifa uchun soddalashtirilgan tahlil ma'lumotini qaytaradi.

    `complaints_count` — shu foydalanuvchiga nisbatan yuborilgan barcha (holatidan
    qat'iy nazar) oldingi shikoyatlar soni. `previous_warnings_count` — shu
    foydalanuvchiga nisbatan tasdiqlangan va ogohlantirish chorasi qo'llanilgan
    oldingi shikoyatlar soni.

    :param complaint: Shikoyat obyektı.
    :return: Tahlil natijasi lug'ati.
    """
    base_qs = (
        Complaint.objects.active()
        .filter(to_user=complaint.to_user)
        .exclude(pk=complaint.pk)
    )

    complaints_count = base_qs.count()
    previous_warnings_count = base_qs.filter(
        status=ComplaintStatus.APPROVED,
        enforcement_action=ComplaintEnforcementAction.WARN,
    ).count()
    previous_blocks_count = base_qs.filter(
        status=ComplaintStatus.APPROVED,
        enforcement_action=ComplaintEnforcementAction.BLOCK,
    ).count()
    previous_actions_count = previous_warnings_count + previous_blocks_count

    if previous_blocks_count >= 1 or previous_actions_count >= 3:
        risk_level, recommendation = "Yuqori", "Profilni bloklash"
    elif previous_actions_count >= 1:
        risk_level, recommendation = "O'rta", "Ogohlantirish yuborish"
    else:
        risk_level, recommendation = "Past", "Qo'shimcha tekshiruv"

    return {
        "risk_level": risk_level,
        "previous_warnings_count": previous_warnings_count,
        "complaints_count": complaints_count,
        "recommended_action": recommendation,
    }


def get_questionnaire_progress(user):
    """
    Foydalanuvchining rolga mos anketa savollariga javob berish progressini hisoblaydi.

    Jami savollar soni foydalanuvchining amaldagi nomzod roli (candidate_type)
    bo'yicha target_gender orqali filtrlanadi — boshqa rolga tegishli savollar
    hisobga kirmaydi.

    :param user: Shikoyat qilingan foydalanuvchi.
    :return: {"answered": int, "total": int, "percentage": int} lug'ati.
    """
    from apps.accounts.questionnaire.models import Question, TargetGender, UserAnswer
    from apps.accounts.questionnaire.services import get_effective_candidate_role

    profile = getattr(user, "profile", None)
    if not profile:
        return {"answered": 0, "total": 0, "percentage": 0}

    answered = UserAnswer.objects.filter(profile=profile, is_active=True).count()
    role = get_effective_candidate_role(profile)
    target_genders = [TargetGender.ALL, role] if role else [TargetGender.ALL]
    total = Question.objects.filter(
        is_active=True, target_gender__in=target_genders
    ).count()
    percentage = round((answered / total) * 100) if total else 0

    return {"answered": answered, "total": total, "percentage": percentage}


def apply_complaint_enforcement(complaint, enforcement_action):
    """
    Tasdiqlangan shikoyat bo'yicha tanlangan chorani amalga oshiradi:
    foydalanuvchiga ogohlantirish yuboradi yoki uni platforma bo'yicha bloklaydi.

    :param complaint: Tasdiqlangan Complaint obyekti.
    :param enforcement_action: ComplaintEnforcementAction qiymati.
    :return: None
    """
    from apps.accounts.notifications.models import Notification
    from apps.accounts.users.services import block_user

    to_user = complaint.to_user

    if enforcement_action == ComplaintEnforcementAction.WARN:
        Notification.objects.create(
            user=to_user,
            title="Ogohlantirish",
            message=(
                f"'{complaint.get_reason_display()}' sababli shikoyatingiz "
                "tasdiqlandi. Qoidabuzarlik davom etsa, profilingiz bloklanadi."
            ),
            extra_data={"complaint_id": str(complaint.id), "action": "warn"},
        )
    elif enforcement_action == ComplaintEnforcementAction.BLOCK:
        block_user(to_user, reason=complaint.get_reason_display(), notify_user=True)
