from django.db import models
from rest_framework.exceptions import ValidationError

from .models import Profile, ProfilePhoto


def create_profile(user, serializer_validated_data):
    """
    Yangi profil yaratish jarayonida target foydalanuvchini aniqlaydi va takroriy profil yaratishni cheklaydi.

    :param user: So'rov yuborayotgan foydalanuvchi (User).
    :param serializer_validated_data: Serializer tomonidan tasdiqlangan ma'lumotlar.
    :return: Profil yaratilayotgan nishon foydalanuvchi obyekti (User).
    :raises ValidationError: Foydalanuvchida allaqachon profil mavjud bo'lsa.
    """
    target_user = user
    requested_user = serializer_validated_data.get("user")
    if requested_user and requested_user != user:
        if not user.has_perm("profiles.add_profile"):
            serializer_validated_data.pop("user", None)
        else:
            target_user = requested_user

    if Profile.objects.filter(user=target_user, is_active=True).exists():
        raise ValidationError(
            {"user": "Ushbu foydalanuvchida allaqachon profil mavjud."}
        )

    return target_user


def update_profile(user, serializer_validated_data):
    """
    Profilni tahrirlashda foydalanuvchining huquqlarini tekshiradi.

    :param user: So'rov yuborayotgan foydalanuvchi (User).
    :param serializer_validated_data: Serializer tomonidan tasdiqlangan ma'lumotlar.
    :return: None
    """
    requested_user = serializer_validated_data.get("user")
    if requested_user and requested_user != user:
        if not user.has_perm("profiles.change_profile"):
            serializer_validated_data.pop("user", None)


def create_profile_photo(user, serializer_validated_data, max_photos=5):
    """
    Profilga yangi rasm yuklashda maksimal rasmlar soni cheklovini tekshiradi va profilni biriktiradi.

    :param user: Foydalanuvchi (User).
    :param serializer_validated_data: Serializer tasdiqlagan ma'lumotlar.
    :param max_photos: Ruxsat etilgan maksimal rasmlar soni (int, default=5).
    :return: Foydalanuvchi profili (Profile) yoki None.
    :raises ValidationError: Maksimal rasmlar sonidan oshib ketgan bo'lsa.
    """
    profile = getattr(user, "profile", None)
    if profile and not serializer_validated_data.get("profile"):
        current_count = ProfilePhoto.objects.filter(
            profile=profile, is_active=True
        ).count()
        if current_count >= max_photos:
            raise ValidationError(
                {
                    "image": (
                        f"Profilga maksimal {max_photos} ta rasm yuklash mumkin. "
                        "Yangi rasm qo'shish uchun avval bitta rasmni o'chiring."
                    )
                }
            )
        return profile
    return None


def verify_user_face(user, uploaded_file):
    """
    Foydalanuvchi yuklagan selfie rasm orqali yuzni tekshiradi (face verification).
    Bloklangan yuzlar bazasi bilan solishtiradi hamda profil rasmlari bilan mosligini tasdiqlaydi.

    :param user: Foydalanuvchi obyekti (User).
    :param uploaded_file: Yuklangan selfie fayli.
    :return: (status_code, response_dict) juftligi.
    """
    from rest_framework import status
    from apps.core.utils.face import (
        _save_as_rgb_jpeg,
        _temp_jpeg_files,
        check_against_blocked_faces,
        extract_embedding,
        hash_compare,
        register_user_faces_as_blocked,
    )

    profile = getattr(user, "profile", None)
    if not profile:
        return status.HTTP_400_BAD_REQUEST, {
            "detail": "Foydalanuvchi profili mavjud emas. Avval profil yarating!"
        }

    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    with _temp_jpeg_files(f"verify_probe_{user.id}") as (temp_path,):
        try:
            _save_as_rgb_jpeg(uploaded_file, temp_path)
            probe_emb = extract_embedding(temp_path)
            if probe_emb:
                is_blocked_match, bf_obj, dist = check_against_blocked_faces(probe_emb)
                if is_blocked_match:
                    user.is_blocked = True
                    user.save(update_fields=["is_blocked"])
                    register_user_faces_as_blocked(
                        user,
                        reason="Bloklangan shaxs yuzi bilan yangi hisob ochishga urinish",
                        embedding=probe_emb,
                    )
                    return status.HTTP_403_FORBIDDEN, {
                        "detail": "Ushbu yuz egasiga tegishli bloklangan hisob aniqlandi! Tizimdan foydalanish taqiqlanadi va ushbu hisobingiz ham bloklandi.",
                        "verified": False,
                        "is_blocked": True,
                    }
        except Exception:
            pass

    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    is_verified, msg = hash_compare(profile, uploaded_file)

    if is_verified:
        return status.HTTP_200_OK, {"message": msg, "verified": True}

    return status.HTTP_400_BAD_REQUEST, {"detail": msg, "verified": False}


def get_nearby_profiles(user, base_queryset, radius_km=10.0):
    """
    Foydalanuvchining GPS nuqtasiga nisbatan berilgan masofa radiusi (radius_km) ichida joylashgan anketalarni topadi.

    :param user: So'rov yuborgan foydalanuvchi.
    :param base_queryset: Asosiy profillar QuerySet-i.
    :param radius_km: Qidiruv radiusi (kilometrlarda, float, default=10.0).
    :return: (user_profile, nearby_profiles_qs) juftligi.
    :raises ValidationError: Foydalanuvchida GPS manzili ko'rsatilmadi bo'lsa.
    """
    user_profile = getattr(user, "profile", None)
    if not user_profile or not user_profile.location:
        raise ValidationError(
            {"detail": "Sizning profilingizda GPS manzilingiz ko'rsatilmagan."}
        )

    if radius_km <= 0:
        radius_km = 10.0

    from django.contrib.gis.db.models.functions import Distance
    from django.contrib.gis.measure import D

    qs = (
        base_queryset.exclude(id=user_profile.id)
        .filter(location__isnull=False)
        .filter(location__distance_lte=(user_profile.location, D(km=radius_km)))
        .annotate(distance=Distance("location", user_profile.location))
        .order_by("distance")
    )
    return user_profile, qs


def send_representative_consent_request(
    user, candidate_contact, kinship_id=None, candidate_role="groom"
):
    """
    Vakil tomonidan nomzodga (kuyov yoki kelin) vakillik so'rovi va bildirishnoma (Notification) yuboradi.

    :param user: Vakil foydalanuvchisi.
    :param candidate_contact: Nomzodning telefon raqami yoki emaili.
    :param kinship_id: Qarindoshlik darajasi ID si.
    :param candidate_role: Nomzodning roli ("groom" yoki "bride").
    :return: (rep_info, target_user) juftligi.
    :raises ValidationError: Kerakli ma'lumotlar to'liq bo'lmasa.
    """
    if not candidate_contact:
        raise ValidationError(
            {"detail": "Nomzodning telefon raqami yoki emaili kiritilishi shart."}
        )

    user_profile = getattr(user, "profile", None)
    if not user_profile:
        raise ValidationError(
            {"detail": "Avval vakil profili yaratilgan bo'lishi kerak."}
        )

    from apps.accounts.users.models import User
    from apps.accounts.notifications.models import Notification
    from .models import RepresentativeInfo

    target_user = User.objects.filter(
        models.Q(phone_number=candidate_contact) | models.Q(email=candidate_contact)
    ).first()

    rep_info, _ = RepresentativeInfo.objects.get_or_create(
        profile=user_profile,
        defaults={
            "kinship_id": kinship_id,
            "candidate_role": candidate_role,
            "candidate_contact": candidate_contact,
            "target_candidate": target_user,
            "is_approved": False,
        },
    )
    rep_info.candidate_contact = candidate_contact
    rep_info.target_candidate = target_user
    rep_info.is_approved = False
    if kinship_id:
        rep_info.kinship_id = kinship_id
    if candidate_role:
        rep_info.candidate_role = candidate_role
    rep_info.save()

    if target_user:
        kinship_name = rep_info.kinship.name if rep_info.kinship else "Vakilingiz"
        rep_profile_id = str(user_profile.id) if user_profile else None
        candidate_profile = getattr(target_user, "profile", None)
        candidate_profile_id = str(candidate_profile.id) if candidate_profile else None

        Notification.objects.create(
            user=target_user,
            title="Vakillik roziligi so'rovi",
            message=f"{user_profile.first_name} ({kinship_name}) sizning nomingizdan anketa to'ldirdi. Rozimisiz?",
            extra_data={
                "type": "representative_consent_request",
                "rep_info_id": str(rep_info.id),
                "representative_user_id": str(user.id),
                "representative_profile_id": rep_profile_id,
                "candidate_user_id": str(target_user.id),
                "candidate_profile_id": candidate_profile_id,
            },
        )

    return rep_info, target_user


def approve_representative_consent(user, rep_info_id=None):
    """
    Nomzod tomonidan vakilning vakillik so'rovi tasdiqlanadi (rozilik beriladi).

    :param user: Rozilik berayotgan nomzod foydalanuvchisi.
    :param rep_info_id: Vakillik ma'lumotlari ID si.
    :return: Yangilangan RepresentativeInfo obyekti.
    :raises ValidationError: Vakillik so'rovi topilmasa.
    """
    from apps.accounts.notifications.models import Notification
    from .models import RepresentativeInfo

    rep_info = RepresentativeInfo.objects.filter(
        models.Q(id=rep_info_id) | models.Q(target_candidate=user)
    ).first()

    if not rep_info:
        raise ValidationError({"detail": "Vakillik so'rovi topilmadi."})

    rep_info.is_approved = True
    rep_info.target_candidate = user
    rep_info.save(update_fields=["is_approved", "target_candidate", "updated_at"])

    if rep_info.profile and rep_info.profile.user:
        candidate_profile = getattr(user, "profile", None)
        candidate_name = (
            candidate_profile.first_name if candidate_profile else user.phone_number
        )
        candidate_profile_id = str(candidate_profile.id) if candidate_profile else None

        Notification.objects.create(
            user=rep_info.profile.user,
            title="Nomzod rozilik berdi!",
            message=f"{candidate_name} sizning vakilligingizga rozilik berdi. Anketa faollashdi.",
            extra_data={
                "type": "representative_consent_approved",
                "rep_info_id": str(rep_info.id),
                "representative_user_id": str(rep_info.profile.user.id),
                "representative_profile_id": str(rep_info.profile.id),
                "candidate_user_id": str(user.id),
                "candidate_profile_id": candidate_profile_id,
            },
        )

    return rep_info


def reject_representative_consent(user, rep_info_id=None):
    """
    Nomzod tomonidan vakillik so'rovi rad etiladi va vakillik yozuvi o'chiriladi.

    :param user: So'rovni rad etayotgan nomzod foydalanuvchisi.
    :param rep_info_id: Vakillik ma'lumotlari ID si.
    :return: None
    :raises ValidationError: Vakillik so'rovi topilmasa.
    """
    from apps.accounts.notifications.models import Notification
    from .models import RepresentativeInfo

    rep_info = RepresentativeInfo.objects.filter(
        models.Q(id=rep_info_id) | models.Q(target_candidate=user)
    ).first()

    if not rep_info:
        raise ValidationError({"detail": "Vakillik so'rovi topilmadi."})

    if rep_info.profile and rep_info.profile.user:
        candidate_profile = getattr(user, "profile", None)
        candidate_name = (
            candidate_profile.first_name if candidate_profile else user.phone_number
        )
        candidate_profile_id = str(candidate_profile.id) if candidate_profile else None

        Notification.objects.create(
            user=rep_info.profile.user,
            title="Vakillik so'rovi rad etildi",
            message=f"{candidate_name} vakillik so'rovini rad etdi.",
            extra_data={
                "type": "representative_consent_rejected",
                "rep_info_id": str(rep_info.id),
                "representative_user_id": str(rep_info.profile.user.id),
                "representative_profile_id": str(rep_info.profile.id),
                "candidate_user_id": str(user.id),
                "candidate_profile_id": candidate_profile_id,
            },
        )

    rep_info.delete()


def filter_profiles_for_user(qs, user):
    """
    So'rov yuborayotgan foydalanuvchining jinsi va nomzodlik rolidan kelib chiqib
    mos anketalarni (kelinlarga kuyovlar, kuyovlarga kelinlar, vakillarga tegishli nomzodlar) filtrlaydi.

    :param qs: Asosiy profillar QuerySet-i.
    :param user: So'rov yuborayotgan foydalanuvchi (User).
    :return: Filtrlangan profillar QuerySet-i.
    """
    if not user or not user.is_authenticated:
        return qs

    if (
        user.is_staff
        or user.is_superuser
        or bool(user.role and not user.role.is_default)
    ):
        return qs

    from apps.accounts.users.models import BlockedUser
    from .models import CandidateRole, GenderType, RepresentativeInfo

    blocked_user_ids = set(
        BlockedUser.objects.filter(blocker=user).values_list("blocked_id", flat=True)
    )
    blocked_by_user_ids = set(
        BlockedUser.objects.filter(blocked=user).values_list("blocker_id", flat=True)
    )
    all_blocked = blocked_user_ids | blocked_by_user_ids
    if all_blocked:
        qs = qs.exclude(user_id__in=all_blocked)

    qs = qs.exclude(user=user)

    user_profile = getattr(user, "profile", None)
    if not user_profile:
        return qs

    if user_profile.candidate_type == CandidateRole.REPRESENTATIVE:
        rep_infos = RepresentativeInfo.objects.filter(profile=user_profile)

        target_user_ids = [
            r.target_candidate_id for r in rep_infos if r.target_candidate_id
        ]
        if target_user_ids:
            qs = qs.exclude(user_id__in=target_user_ids)

        roles = set()
        for rep in rep_infos:
            if rep.candidate_role:
                roles.add(rep.candidate_role)
            if rep.target_candidate_id and hasattr(rep.target_candidate, "profile"):
                target_prof = rep.target_candidate.profile
                if target_prof.candidate_type in [
                    CandidateRole.GROOM,
                    CandidateRole.BRIDE,
                ]:
                    roles.add(target_prof.candidate_type)
                elif target_prof.gender == GenderType.MALE:
                    roles.add(CandidateRole.GROOM)
                elif target_prof.gender == GenderType.FEMALE:
                    roles.add(CandidateRole.BRIDE)

        has_groom = CandidateRole.GROOM in roles
        has_bride = CandidateRole.BRIDE in roles

        if has_groom and has_bride:
            return qs.exclude(candidate_type=CandidateRole.REPRESENTATIVE)
        elif has_groom:
            return qs.filter(
                models.Q(gender=GenderType.FEMALE)
                | models.Q(candidate_type=CandidateRole.BRIDE)
            ).exclude(candidate_type=CandidateRole.REPRESENTATIVE)
        elif has_bride:
            return qs.filter(
                models.Q(gender=GenderType.MALE)
                | models.Q(candidate_type=CandidateRole.GROOM)
            ).exclude(candidate_type=CandidateRole.REPRESENTATIVE)
        else:
            return qs.exclude(candidate_type=CandidateRole.REPRESENTATIVE)

    is_groom = (
        user_profile.candidate_type == CandidateRole.GROOM
        or user_profile.gender == GenderType.MALE
    )
    is_bride = (
        user_profile.candidate_type == CandidateRole.BRIDE
        or user_profile.gender == GenderType.FEMALE
    )

    if is_groom and not is_bride:
        return qs.filter(
            models.Q(gender=GenderType.FEMALE)
            | models.Q(candidate_type=CandidateRole.BRIDE)
        ).exclude(candidate_type=CandidateRole.REPRESENTATIVE)
    elif is_bride and not is_groom:
        return qs.filter(
            models.Q(gender=GenderType.MALE)
            | models.Q(candidate_type=CandidateRole.GROOM)
        ).exclude(candidate_type=CandidateRole.REPRESENTATIVE)

    return qs.exclude(candidate_type=CandidateRole.REPRESENTATIVE)


MAX_SAVED_PROFILES = 10


def save_profile_for_user(user, profile_id):
    """
    Foydalanuvchi uchun berilgan profile_id bo'yicha anketani saqlaydi. Max 10 ta cheklovni tekshiradi.

    :param user: So'rov yuborayotgan foydalanuvchi.
    :param profile_id: Saqlanayotgan profil ID si.
    :return: Yaratilgan yoki yangilangan SavedProfile obyekti.
    :raises ValidationError: Limit oshganda yoki o'z profilini saqlamoqchi bo'lganda.
    """
    from .models import Profile, SavedProfile

    if not user or not user.is_authenticated:
        raise ValidationError({"detail": "Avtorizatsiyadan o'tishingiz shart."})

    profile = Profile.objects.filter(id=profile_id, is_active=True).first()
    if not profile:
        raise ValidationError({"detail": "Saqlanayotgan profil topilmadi."})

    user_profile = getattr(user, "profile", None)
    if user_profile and str(user_profile.id) == str(profile.id):
        raise ValidationError({"detail": "O'zingizning profilingizni saqlay olmaysiz."})

    existing = SavedProfile.objects.filter(user=user, saved_profile=profile).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.save(update_fields=["is_active", "updated_at"])
        return existing

    current_count = SavedProfile.objects.filter(user=user, is_active=True).count()
    if current_count >= MAX_SAVED_PROFILES:
        raise ValidationError(
            {
                "detail": (
                    f"Saqlangan anketalar soni maksimal {MAX_SAVED_PROFILES} taga yetgan. "
                    "Yangi nomzod qo'shish uchun avval bittasini saqlanganlardan o'chiring."
                )
            }
        )

    saved_obj = SavedProfile.objects.create(user=user, saved_profile=profile)
    return saved_obj


def unsave_profile_for_user(user, profile_id):
    """
    Saqlangan profilni foydalanuvchining saqlanganlar ro'yxatidan o'chiradi.

    :param user: Foydalanuvchi obyekti.
    :param profile_id: Saqlanganlardan chiqarilayotgan profil ID si.
    :return: True bo'lsa muvaffaqiyatli.
    :raises ValidationError: Profil saqlanganlar ro'yxatida topilmasa.
    """
    from .models import SavedProfile

    if not user or not user.is_authenticated:
        raise ValidationError({"detail": "Avtorizatsiyadan o'tishingiz shart."})

    saved_obj = SavedProfile.objects.filter(
        user=user, saved_profile_id=profile_id, is_active=True
    ).first()

    if not saved_obj:
        raise ValidationError(
            {"detail": "Ushbu profil saqlanganlar ro'yxatida topilmadi."}
        )

    saved_obj.hard_delete()
    return True


def get_saved_profile_ids_for_user(user):
    """
    Foydalanuvchi saqlagan anketalarning ID lari to'plamini (set) qaytaradi.

    :param user: Foydalanuvchi obyekti.
    :return: Profil ID lari to'plami (set of UUIDs).
    """
    from .models import SavedProfile

    if not user or not user.is_authenticated:
        return set()

    return set(
        SavedProfile.objects.filter(user=user, is_active=True).values_list(
            "saved_profile_id", flat=True
        )
    )


def get_saved_profiles_for_user(user):
    """
    Foydalanuvchi saqlagan barcha active Profile anketalari QuerySet-ini hamda ID lar to'plamini qaytaradi.

    :param user: Foydalanuvchi obyekti.
    :return: (profiles_qs, saved_profile_ids_set) juftligi.
    """
    from .models import Profile

    saved_profile_ids = get_saved_profile_ids_for_user(user)

    qs = (
        Profile.objects.select_related("user", "user__role", "region", "district")
        .prefetch_related("photos")
        .filter(id__in=saved_profile_ids)
        .active()
    )

    return qs, saved_profile_ids


def get_saved_profile_objects_for_user(user):
    """
    Foydalanuvchining SavedProfile modelining faol obyektlari QuerySet-ini qaytaradi.

    :param user: Foydalanuvchi obyekti.
    :return: SavedProfile QuerySet-i.
    """
    from .models import SavedProfile

    if not user or not user.is_authenticated:
        return SavedProfile.objects.none()

    return SavedProfile.objects.filter(user=user).active()


def get_paginated_profiles_response(
    view_instance, request, queryset, extra_context=None, only_matched=False
):
    """
    Profillar queryset-ini filtrlaydi, paginatsiya qiladi, moslik ballarini (batch scores)
    va saqlangan profillar ma'lumotlarini serializer kontekstiga qo'shib, Response obyektini qaytaradi.
    Agar only_matched=True bo'lsa, faqat moslik bali aniqlangan nomzodlarni chiqaradi.

    :param view_instance: DRF ViewSet instansiyasi (self).
    :param request: HTTP Request obyekti.
    :param queryset: Profillar QuerySet-i.
    :param extra_context: Serializer kontekstiga qo'shimcha kiritiladigan lug'at (dict).
    :param only_matched: True bo'lsa, faqat moslik bali aniqlangan nomzodlarni va moslik foizi bo'yicha kamayish tartibida qaytaradi.
    :return: DRF Response (Response).
    """
    from rest_framework.response import Response
    from apps.accounts.questionnaire.services import (
        batch_calculate_compatibility_scores,
    )

    user_profile = (
        getattr(request.user, "profile", None)
        if request.user and request.user.is_authenticated
        else None
    )

    qs = view_instance.filter_queryset(queryset)

    if only_matched:
        if not user_profile:
            page = view_instance.paginate_queryset([])
            if page is not None:
                return view_instance.get_paginated_response([])
            return Response([])

        all_candidates = list(qs)
        batch_scores = (
            batch_calculate_compatibility_scores(user_profile, all_candidates)
            if all_candidates
            else {}
        )

        matched_candidates = [
            p for p in all_candidates if batch_scores.get(p.id) is not None
        ]

        matched_candidates.sort(
            key=lambda p: (batch_scores.get(p.id) or {}).get("overall_score", 0),
            reverse=True,
        )

        page = view_instance.paginate_queryset(matched_candidates)
        items = list(page) if page is not None else matched_candidates

        context = view_instance.get_serializer_context()
        context["batch_compatibility_scores"] = batch_scores

        if extra_context:
            context.update(extra_context)

        if page is not None:
            serializer = view_instance.get_serializer(items, many=True, context=context)
            return view_instance.get_paginated_response(serializer.data)

        serializer = view_instance.get_serializer(
            matched_candidates, many=True, context=context
        )
        return Response(serializer.data)

    page = view_instance.paginate_queryset(qs)

    context = view_instance.get_serializer_context()

    if extra_context:
        context.update(extra_context)

    if page is not None:
        serializer = view_instance.get_serializer(page, many=True, context=context)
        return view_instance.get_paginated_response(serializer.data)

    serializer = view_instance.get_serializer(qs, many=True, context=context)
    return Response(serializer.data)
