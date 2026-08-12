from django.db import models
from rest_framework.exceptions import ValidationError

from .models import Profile, ProfilePhoto


def create_profile(user, serializer_validated_data):
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
    requested_user = serializer_validated_data.get("user")
    if requested_user and requested_user != user:
        if not user.has_perm("profiles.change_profile"):
            serializer_validated_data.pop("user", None)


def create_profile_photo(user, serializer_validated_data, max_photos=5):
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
