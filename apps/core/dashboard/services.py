"""Boshqaruv paneli uchun umumlashgan statistika hisob-kitoblari.

Har bir koʻrsatkich alohida funksiyada hisoblanadi. Hali modeli yoʻq
koʻrsatkichlar (nikoh natijasi, profil moderatsiya navbati, sunʼiy intellekt
signallari) hozircha 0 / null qaytaradi — tegishli model yaratilganda faqat shu
funksiyalar ichi almashtiriladi, `get_dashboard_summary` javob shakli oʻzgarmaydi.
"""

from datetime import timedelta

from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.accounts.complaints.models import Complaint, ComplaintStatus
from apps.accounts.profiles.models import CandidateRole, GenderType, Profile
from apps.accounts.questionnaire.models import Question, TargetGender
from apps.accounts.users.models import User
from apps.matches.chats.models import ChatRoom
from apps.matches.match_requests.models import MatchRequest, MatchRequestStatus

# Suhbat "faol" hisoblanishi uchun oxirgi xabar shu oyna ichida boʻlishi kerak
ACTIVE_CHAT_WINDOW_HOURS = 24


def _end_users_qs():
    """Oddiy foydalanuvchilar (xodim/moderator boʻlmaganlar) queryseti."""
    return (
        User.objects.filter(is_active=True)
        .exclude(is_staff=True)
        .exclude(role__is_default=False)
    )


def count_total_users():
    """Platformadagi jami oddiy foydalanuvchilar soni."""
    return _end_users_qs().count()


def count_users_joined_last_days(days):
    """Oxirgi `days` kun ichida qoʻshilgan oddiy foydalanuvchilar soni."""
    since = timezone.now() - timedelta(days=days)
    return _end_users_qs().filter(created_at__gte=since).count()


def _end_user_profiles_qs():
    """Oddiy foydalanuvchilarga tegishli profillar queryseti."""
    return Profile.objects.filter(is_active=True, user__in=_end_users_qs())


def count_profiles():
    """Anketa (profil) toʻldirgan oddiy foydalanuvchilar soni."""
    return _end_user_profiles_qs().count()


def profile_conversion_pct():
    """Anketa toʻldirish konversiyasi (profillar / foydalanuvchilar), foizda (0–100)."""
    users = count_total_users()
    if not users:
        return 0
    return min(100, round(count_profiles() / users * 100))


def count_active_chats():
    """Oxirgi 24 soatda xabar boʻlgan faol suhbatlar soni."""
    since = timezone.now() - timedelta(hours=ACTIVE_CHAT_WINDOW_HOURS)
    return (
        ChatRoom.objects.filter(
            is_active=True,
            messages__is_active=True,
            messages__created_at__gte=since,
        )
        .distinct()
        .count()
    )


def _daily_series(queryset, days, start):
    """`queryset` ni `created_at` sanasi boʻyicha kunlik sanoq roʻyxatiga aylantiradi.

    Natija — `days` ta butun son; `start` kunidan bugungacha, boʻsh kunlar 0.
    """
    rows = (
        queryset.filter(created_at__date__gte=start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
    )
    counts = {row["day"]: row["total"] for row in rows}
    return [counts.get(start + timedelta(days=i), 0) for i in range(days)]


def get_trend(days):
    """Roʻyxatdan oʻtish / anketa / mosliklar boʻyicha kunlik dinamika."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    return {
        "days": [(start + timedelta(days=i)).isoformat() for i in range(days)],
        "registrations": _daily_series(_end_users_qs(), days, start),
        "questionnaires": _daily_series(_end_user_profiles_qs(), days, start),
        "matches": _daily_series(
            MatchRequest.objects.filter(
                is_active=True, status=MatchRequestStatus.ACCEPTED
            ),
            days,
            start,
        ),
    }


def _questionnaire_completed_count():
    """Amaldagi rolига mos barcha savollarga javob bergan profillar soni.

    "Tugallangan" mezoni `complaints/services.py: get_questionnaire_progress` bilan
    bir xil: jami savollar profil roli boʻyicha `target_gender` orqali filtrlanadi
    (kuyov faqat kuyov + umumiy savollarni koʻradi). Bitta soʻrov — N+1 yoʻq.
    """
    groom_total = Question.objects.filter(
        is_active=True, target_gender__in=[TargetGender.ALL, TargetGender.GROOM]
    ).count()
    bride_total = Question.objects.filter(
        is_active=True, target_gender__in=[TargetGender.ALL, TargetGender.BRIDE]
    ).count()
    if not groom_total and not bride_total:
        return 0

    return (
        _end_user_profiles_qs()
        .annotate(
            answered=Count("answers", filter=Q(answers__is_active=True), distinct=True),
            required=Case(
                When(candidate_type=CandidateRole.GROOM, then=Value(groom_total)),
                When(candidate_type=CandidateRole.BRIDE, then=Value(bride_total)),
                When(gender=GenderType.MALE, then=Value(groom_total)),
                When(gender=GenderType.FEMALE, then=Value(bride_total)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        .filter(required__gt=0, answered__gte=F("required"))
        .count()
    )


def get_funnel():
    """Anketa toʻldirish voronkasi bosqichlari."""
    questions_done = _questionnaire_completed_count()

    request_sent = (
        MatchRequest.objects.filter(is_active=True)
        .values("from_profile")
        .distinct()
        .count()
    )
    chat_started = (
        ChatRoom.objects.filter(is_active=True)
        .values("match_request__from_profile")
        .distinct()
        .count()
    )
    return {
        "registered": count_total_users(),
        "profile_filled": count_profiles(),
        "questions_done": questions_done,
        "request_sent": request_sent,
        "chat_started": chat_started,
    }


def count_open_complaints():
    """Koʻrib chiqilishi kutilayotgan shikoyatlar soni."""
    return Complaint.objects.filter(
        is_active=True, status=ComplaintStatus.PENDING
    ).count()


# --- Hali modeli yoʻq koʻrsatkichlar ---
# Tegishli model yaratilganda shu funksiyalar ichidagi qiymat real hisob-kitob
# bilan almashtiriladi; response shakli va endpoint oʻzgarmaydi.


def count_married():
    """Nikohga yetgan juftliklar soni.

    TODO(success-story): nikoh natijasini saqlovchi model (Profile.outcome yoki
    alohida SuccessStory) yaratilganda shu yerdan olinadi.
    """
    return 0


def married_delta_month():
    """Oxirgi 30 kunda nikohga yetganlar oʻsishi.

    TODO(success-story): count_married bilan birga qoʻshiladi.
    """
    return


def count_pending_profile_moderation():
    """Selfi va rasm tekshiruvi kutayotgan profillar soni.

    TODO(moderation): profil moderatsiya navbati modeli yoki
    Profile.moderation_status maydoni yaratilganda shu yerdan olinadi.
    """
    return 0


def count_ai_signals():
    """Suhbatlardagi sunʼiy intellekt signallari soni.

    TODO(ai-signals): suhbat xabarlarini tahlil qiluvchi signal modeli
    yaratilganda shu yerdan olinadi.
    """
    return 0


def get_dashboard_summary(days):
    """Boshqaruv paneli uchun barcha koʻrsatkichlarni bitta lugʻatga yigʻadi."""
    return {
        "totals": {
            "users": {
                "value": count_total_users(),
                "delta_week": count_users_joined_last_days(7),
            },
            "profiles_filled": {
                "value": count_profiles(),
                "conversion_pct": profile_conversion_pct(),
            },
            "active_chats": {"value": count_active_chats()},
            "married": {
                "value": count_married(),
                "delta_month": married_delta_month(),
            },
        },
        "trend": get_trend(days),
        "funnel": get_funnel(),
        "tasks": {
            "profile_moderation": count_pending_profile_moderation(),
            "ai_signals": count_ai_signals(),
            "complaints_open": count_open_complaints(),
        },
    }
