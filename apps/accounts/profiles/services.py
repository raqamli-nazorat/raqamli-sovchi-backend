from rest_framework.exceptions import ValidationError

from .models import Profile, ProfilePhoto


def create_profile(user, serializer_validated_data):
    target_user = user
    if (user.is_staff or user.is_superuser) and serializer_validated_data.get("user"):
        target_user = serializer_validated_data["user"]

    if Profile.objects.filter(user=target_user, is_active=True).exists():
        raise ValidationError(
            {"user": "Ushbu foydalanuvchida allaqachon profil mavjud."}
        )

    return target_user


def update_profile(user, serializer_validated_data):
    if not (user.is_staff or user.is_superuser):
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
