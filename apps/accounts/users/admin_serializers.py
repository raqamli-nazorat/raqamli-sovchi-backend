from datetime import date

from rest_framework import serializers

from apps.accounts.complaints.models import Complaint
from apps.accounts.profiles.models import RepresentativeInfo
from apps.core.base.serializers import BaseModelSerializer
from apps.matches.match_requests.models import MatchRequest

from .models import User


def _mask_phone(phone):
    """Telefon raqamning o'rta qismini yashiradi: +998 90 *** 41 22."""
    if not phone or len(phone) < 9:
        return phone
    return f"{phone[:7]}***{phone[-4:]}"


def _build_photo_url(photo, request):
    """Rasm URL sini to'liq (absolute) shaklga keltiradi."""
    if not photo or not photo.image:
        return None
    return request.build_absolute_uri(photo.image.url) if request else photo.image.url


def _get_main_photo_url(photos_qs, request):
    """Profile rasmlari ichidan asosiy rasmning URL sini qaytaradi."""
    photos = list(photos_qs)
    main = next((p for p in photos if p.is_main), None) or next(iter(photos), None)
    return _build_photo_url(main, request)


def _compute_age(birth_date):
    """Tug'ilgan sanadan yoshni hisoblaydi."""
    if not birth_date:
        return None
    today = date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def _get_user_status(user):
    """Foydalanuvchi holatini (Tasdiqlangan/Tekshiruvda/Bloklangan) qaytaradi."""
    if user.is_blocked:
        return "Bloklangan"
    if not user.is_verified:
        return "Tekshiruvda"
    return "Tasdiqlangan"


def _guardian_dates(rep_info):
    """Vakillik jarayonidagi asosiy sanalarni (ariza, tasdiq, anketa) qaytaradi."""
    profile = rep_info.profile
    questionnaire_date = None
    last_answer = (
        profile.answers.order_by("-created_at").first()
        if hasattr(profile, "answers")
        else None
    )
    if last_answer:
        questionnaire_date = last_answer.created_at

    approved_date = None
    if rep_info.is_approved:
        try:
            from auditlog.models import LogEntry
            from django.contrib.contenttypes.models import ContentType

            ct = ContentType.objects.get_for_model(RepresentativeInfo)
            entry = (
                LogEntry.objects.filter(
                    content_type=ct,
                    object_id=str(rep_info.pk),
                    action=LogEntry.Action.UPDATE,
                )
                .filter(changes__contains='"is_approved"')
                .order_by("timestamp")
                .last()
            )
            if entry:
                approved_date = entry.timestamp
        except Exception:
            pass

    return {
        "application_date": rep_info.created_at,
        "sms_sent_date": None,
        "approved_date": approved_date,
        "questionnaire_date": questionnaire_date,
    }


def _serialize_guardian(rep_info):
    """Vakil (RepresentativeInfo) obyektini admin detail uchun dict ko'rinishida qaytaradi."""
    profile = rep_info.profile
    rep_user = getattr(profile, "user", None)
    return {
        "id": str(rep_info.id),
        "display_id": (
            f"USR-{str(rep_user.id).replace('-', '')[:5].upper()}" if rep_user else None
        ),
        "name": f"{profile.first_name or ''} {profile.last_name or ''}".strip(),
        "age": _compute_age(profile.birth_date),
        "status": _get_user_status(rep_user) if rep_user else None,
        "phone": rep_user.phone_number if rep_user else None,
        "kinship": rep_info.kinship.name if rep_info.kinship else None,
        "candidate_role": rep_info.get_candidate_role_display(),
        "is_approved": rep_info.is_approved,
        "candidates_count": sum(
            1 for ri in profile.representative_infos.all() if ri.is_active
        ),
        "region": profile.region.name if profile.region else None,
        "district": profile.district.name if profile.district else None,
        "dates": _guardian_dates(rep_info),
        "created_at": rep_info.created_at,
    }


class AdminUserListSerializer(BaseModelSerializer):
    """Admin panel jadval ro'yxati uchun serializer — faqat ustun maydonlari."""

    display_id = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    main_photo = serializers.SerializerMethodField()
    candidate_type = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    region_name = serializers.SerializerMethodField()
    district_name = serializers.SerializerMethodField()
    questionnaire_percent = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "display_id",
            "full_name",
            "main_photo",
            "candidate_type",
            "region_name",
            "district_name",
            "role_name",
            "auth_provider",
            "questionnaire_percent",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_display_id(self, obj):
        """USR-XXXXX formatidagi qisqa identifikator."""
        return f"USR-{str(obj.id).replace('-', '')[:5].upper()}"

    def get_full_name(self, obj):
        """Profildan to'liq ismni oladi; yo'q bo'lsa telefon/emailni qaytaradi."""
        profile = getattr(obj, "profile", None)
        if profile and (profile.first_name or profile.last_name):
            return f"{profile.first_name or ''} {profile.last_name or ''}".strip()
        return obj.phone_number or obj.email or ""

    def get_main_photo(self, obj):
        """Asosiy profil rasmi URL si."""
        profile = getattr(obj, "profile", None)
        if not profile:
            return None
        return _get_main_photo_url(profile.photos.all(), self.context.get("request"))

    def get_candidate_type(self, obj):
        """Nomzod turi: Kuyov/Kelin/Vakil."""
        profile = getattr(obj, "profile", None)
        if profile and profile.candidate_type:
            return profile.get_candidate_type_display()
        return None

    def get_role_name(self, obj):
        """Rol nomi."""
        return obj.role.name if obj.role else None

    def get_region_name(self, obj):
        """Viloyat nomi."""
        profile = getattr(obj, "profile", None)
        return profile.region.name if profile and profile.region_id else None

    def get_district_name(self, obj):
        """Tuman nomi."""
        profile = getattr(obj, "profile", None)
        return profile.district.name if profile and profile.district_id else None

    def get_questionnaire_percent(self, obj):
        """Javob berilgan savollar ulushi (0-100). Context'dan total_questions olinadi."""
        answered = getattr(obj, "answered_count", 0) or 0
        total = self.context.get("total_questions", 30)
        if not total:
            return 0
        return min(round(answered / total * 100), 100)

    def get_status(self, obj):
        """Foydalanuvchi holati."""
        return _get_user_status(obj)


class AdminUserDetailSerializer(BaseModelSerializer):
    """Admin panel to'liq detail sahifasi uchun serializer — barcha bo'limlar bitta javobda."""

    display_id = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    personal = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    photos = serializers.SerializerMethodField()
    questionnaire = serializers.SerializerMethodField()
    guardian = serializers.SerializerMethodField()
    account = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "display_id",
            "full_name",
            "status",
            "personal",
            "contact",
            "photos",
            "questionnaire",
            "guardian",
            "account",
        ]

    def get_display_id(self, obj):
        """USR-XXXXX formatidagi qisqa identifikator."""
        return f"USR-{str(obj.id).replace('-', '')[:5].upper()}"

    def get_full_name(self, obj):
        """To'liq ism yoki telefon/email."""
        profile = getattr(obj, "profile", None)
        if profile and (profile.first_name or profile.last_name):
            return f"{profile.first_name or ''} {profile.last_name or ''}".strip()
        return obj.phone_number or obj.email or ""

    def get_status(self, obj):
        """Foydalanuvchi holati."""
        return _get_user_status(obj)

    def get_personal(self, obj):
        """Shaxsiy ma'lumotlar bo'limi."""
        profile = getattr(obj, "profile", None)
        if not profile:
            return None
        return {
            "age": _compute_age(profile.birth_date),
            "birth_date": profile.birth_date,
            "height": profile.height,
            "weight": profile.weight,
            "gender": profile.get_gender_display() if profile.gender else None,
            "candidate_type": profile.get_candidate_type_display()
            if profile.candidate_type
            else None,
            "nationality": {
                "id": str(profile.nationality.id),
                "name": profile.nationality.name,
            }
            if profile.nationality
            else None,
            "profession": {
                "id": str(profile.profession.id),
                "name": profile.profession.name,
            }
            if profile.profession
            else None,
            "education_level": {
                "id": str(profile.education_level.id),
                "name": profile.education_level.name,
            }
            if profile.education_level
            else None,
            "marital_status": {
                "id": str(profile.marital_status.id),
                "name": profile.marital_status.name,
            }
            if profile.marital_status
            else None,
            "health_status": {
                "id": str(profile.health_status.id),
                "name": profile.health_status.name,
            }
            if profile.health_status
            else None,
            "has_children": profile.has_children,
            "children_count": profile.children_count,
        }

    def get_contact(self, obj):
        """Aloqa va manzil ma'lumotlari bo'limi."""
        profile = getattr(obj, "profile", None)
        request = self.context.get("request")
        voice_url = None
        if profile and profile.voice_intro:
            voice_url = (
                request.build_absolute_uri(profile.voice_intro.url)
                if request
                else profile.voice_intro.url
            )
        return {
            "region": {"id": str(profile.region.id), "name": profile.region.name}
            if profile and profile.region
            else None,
            "district": {"id": str(profile.district.id), "name": profile.district.name}
            if profile and profile.district
            else None,
            "phone_masked": _mask_phone(obj.phone_number),
            "email": obj.email,
            "auth_provider": obj.get_auth_provider_display(),
            "bio": profile.bio if profile else None,
            "voice_intro_url": voice_url,
        }

    def get_photos(self, obj):
        """Profil rasmlari ro'yxati."""
        profile = getattr(obj, "profile", None)
        if not profile:
            return []
        request = self.context.get("request")
        return [
            {
                "id": str(photo.id),
                "url": _build_photo_url(photo, request),
                "is_main": photo.is_main,
                "order": photo.order,
            }
            for photo in profile.photos.all()
        ]

    def get_questionnaire(self, obj):
        """Anketa natijalari: bo'limlar bo'yicha ballar (0-4.0 shkala)."""
        profile = getattr(obj, "profile", None)
        if not profile:
            return {"answered": 0, "sections": []}

        section_data = {}
        total_answered = 0

        for answer in profile.answers.all():
            if not answer.is_active:
                continue
            total_answered += 1
            section = (
                getattr(answer.question, "section", None) if answer.question else None
            )
            if not section:
                continue
            sec_name = section.name
            if sec_name not in section_data:
                section_data[sec_name] = {"weight_sum": 0, "count": 0}
            section_data[sec_name]["weight_sum"] += answer.selected_option.weight
            section_data[sec_name]["count"] += 1

        sections = []
        for sec_name, data in section_data.items():
            if data["count"] > 0:
                # 0-10 og'irlik shkalasini 0-4.0 ko'rinishiga normallashtirish
                score = round((data["weight_sum"] / (data["count"] * 10)) * 4.0, 1)
                sections.append(
                    {
                        "name": sec_name,
                        "score": score,
                        "max_score": 4.0,
                        "answered": data["count"],
                    }
                )

        return {"answered": total_answered, "sections": sections}

    def get_guardian(self, obj):
        """Foydalanuvchining eng oxirgi vakili ma'lumotlari (represented_by_infos orqali)."""
        rep_info = (
            obj.represented_by_infos.filter(is_active=True)
            .order_by("-created_at")
            .first()
        )
        if not rep_info:
            return None
        return _serialize_guardian(rep_info)

    def get_account(self, obj):
        """Hisob ma'lumotlari bo'limi (o'ng panel uchun)."""
        has_guardian = obj.represented_by_infos.filter(is_active=True).exists()
        profile = getattr(obj, "profile", None)
        return {
            "display_id": f"USR-{str(obj.id).replace('-', '')[:5].upper()}",
            "role": {"id": str(obj.role.id), "name": obj.role.name}
            if obj.role
            else None,
            "management_type": "Vakil orqali" if has_guardian else "Mustaqil",
            "candidate_type": profile.get_candidate_type_display()
            if profile and profile.candidate_type
            else None,
            "auth_provider": obj.get_auth_provider_display(),
            "is_verified": obj.is_verified,
            "is_blocked": obj.is_blocked,
            "created_at": obj.created_at,
            "deactivated_at": obj.updated_at if not obj.is_active else None,
        }


class AdminUserBlockSerializer(serializers.Serializer):
    """Admin tomonidan foydalanuvchini bloklash uchun serializer."""

    REASON_CHOICES = [
        ("fraud", "Firibgarlik belgilari"),
        ("fake_profile", "Soxta profil"),
        ("abusive_language", "Odobsiz xulq"),
        ("spam", "Spam va reklama"),
        ("other", "Boshqa"),
    ]

    reason = serializers.ChoiceField(choices=REASON_CHOICES)
    notify_user = serializers.BooleanField(default=False, required=False)


class AdminUserComplaintSerializer(BaseModelSerializer):
    """Foydalanuvchiga kelib tushgan shikoyatlar ro'yxati uchun serializer."""

    from_user_name = serializers.SerializerMethodField()
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "from_user_name",
            "reason",
            "reason_label",
            "status",
            "status_label",
            "created_at",
        ]

    def get_from_user_name(self, obj):
        """Shikoyat yuboruvchining to'liq ismini qaytaradi."""
        profile = getattr(obj.from_user, "profile", None)
        if profile and (profile.first_name or profile.last_name):
            return f"{profile.first_name or ''} {profile.last_name or ''}".strip()
        return obj.from_user.phone_number or obj.from_user.email or ""


class AdminUserMatchHistorySerializer(BaseModelSerializer):
    """Foydalanuvchi moslik so'rovlari tarixi uchun serializer."""

    partner_name = serializers.SerializerMethodField()
    partner_photo = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = MatchRequest
        fields = [
            "id",
            "partner_name",
            "partner_photo",
            "direction",
            "status",
            "status_label",
            "created_at",
        ]

    def _get_partner(self, obj):
        """So'rov yo'nalishiga qarab sherik profilini aniqlaydi."""
        user_profile = self.context.get("user_profile")
        if user_profile and obj.from_profile_id == user_profile.id:
            return obj.to_profile
        return obj.from_profile

    def get_partner_name(self, obj):
        """Sherik nomzodning to'liq ismi."""
        partner = self._get_partner(obj)
        if not partner:
            return None
        return f"{partner.first_name} {partner.last_name}".strip()

    def get_partner_photo(self, obj):
        """Sherik nomzodning asosiy rasmi URL si."""
        partner = self._get_partner(obj)
        if not partner:
            return None
        return _get_main_photo_url(partner.photos.all(), self.context.get("request"))

    def get_direction(self, obj):
        """So'rov yo'nalishi: yuborilgan yoki qabul_qilingan."""
        user_profile = self.context.get("user_profile")
        if user_profile and obj.from_profile_id == user_profile.id:
            return "yuborilgan"
        return "qabul_qilingan"


def build_user_history(user):
    """
    Foydalanuvchi tarixiy voqealar ro'yxatini qurib qaytaradi.
    Voqealar yangirogidan eskisiga tartibda keladi.
    """
    from apps.accounts.questionnaire.models import Question, TargetGender, UserAnswer
    from apps.accounts.questionnaire.services import get_effective_candidate_role

    events = []
    profile = getattr(user, "profile", None)

    # Profil yaratildi
    if profile:
        events.append(
            {
                "event_type": "profile_created",
                "label": "Profil yaratildi",
                "actor": "Avtomatik",
                "date": profile.created_at,
                "is_done": True,
            }
        )

    # Halollik qasami qabul qilindi
    try:
        pledge = user.pledge
        if pledge.is_active:
            events.append(
                {
                    "event_type": "pledge_accepted",
                    "label": "Halollik qasami qabul qilindi",
                    "actor": "Avtomatik",
                    "date": pledge.created_at,
                    "is_done": True,
                }
            )
    except Exception:
        pass

    # Anketa yakunlandi — jami savol soni foydalanuvchining jinsi/roliga mos savollar
    # (target_gender) bo'yicha hisoblanadi, aks holda boshqa jinsga tegishli savollar
    # ham hisobga kirib, anketa hech qachon "bajarildi" bo'lmay qoladi.
    if profile:
        answered = UserAnswer.objects.filter(profile=profile, is_active=True).count()
        role = get_effective_candidate_role(profile)
        target_genders = [TargetGender.ALL, role] if role else [TargetGender.ALL]
        total = Question.objects.filter(
            is_active=True, target_gender__in=target_genders
        ).count()
        if answered > 0:
            last_answer = (
                UserAnswer.objects.filter(profile=profile, is_active=True)
                .order_by("-created_at")
                .first()
            )
            events.append(
                {
                    "event_type": "questionnaire_done",
                    "label": f"Anketa {answered}/{total} yakunlandi",
                    "actor": "Avtomatik",
                    "date": last_answer.created_at,
                    "is_done": total > 0 and answered >= total,
                }
            )

    # Selfi tasdiqlandi — audit log orqali
    if user.is_verified:
        try:
            from auditlog.models import LogEntry
            from django.contrib.contenttypes.models import ContentType

            ct = ContentType.objects.get_for_model(User)
            entry = (
                LogEntry.objects.filter(
                    content_type=ct,
                    object_id=str(user.pk),
                    action=LogEntry.Action.UPDATE,
                )
                .filter(changes__contains='"is_verified"')
                .order_by("timestamp")
                .last()
            )
            if entry:
                actor_name = "Avtomatik"
                if entry.actor:
                    actor_profile = getattr(entry.actor, "profile", None)
                    if actor_profile and (
                        actor_profile.first_name or actor_profile.last_name
                    ):
                        first = actor_profile.first_name or ""
                        last = actor_profile.last_name or ""
                        actor_name = f"{first[0]}. {last}".strip() if first else last
                    else:
                        actor_name = entry.actor.phone_number or "Admin"
                events.append(
                    {
                        "event_type": "selfie_verified",
                        "label": "Selfi tasdiqlandi",
                        "actor": actor_name,
                        "date": entry.timestamp,
                        "is_done": True,
                    }
                )
        except Exception:
            pass

    # Vakil biriktirildi
    reps = user.represented_by_infos.filter(is_active=True).order_by("created_at")
    for rep in reps:
        events.append(
            {
                "event_type": "representative_assigned",
                "label": "Vakil biriktirildi",
                "actor": "Avtomatik",
                "date": rep.created_at,
                "is_done": True,
            }
        )

    events.sort(key=lambda x: x["date"] or "", reverse=True)
    return events


class AdminUserHistorySerializer(serializers.Serializer):
    """Foydalanuvchi tarix voqeasi uchun serializer."""

    event_type = serializers.CharField()
    label = serializers.CharField()
    actor = serializers.CharField()
    date = serializers.DateTimeField()
    is_done = serializers.BooleanField()
