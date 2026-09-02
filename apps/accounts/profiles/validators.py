import os

import mutagen
from rest_framework import serializers

from apps.core.utils.face import verify_face_image

ALLOWED_AUDIO_EXTENSIONS = {"mp3", "ogg", "m4a", "aac", "wav", "opus"}
ALLOWED_AUDIO_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/mp4",
    "audio/m4a",
    "audio/aac",
    "audio/x-aac",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/opus",
    "audio/webm",
}
MAX_VOICE_DURATION_SECONDS = 60
MAX_PHOTOS_PER_PROFILE = 5


def validate_voice_intro(value):
    if not value:
        return value

    filename = getattr(value, "name", "") or ""
    ext = os.path.splitext(filename)[-1].lstrip(".").lower()
    content_type = getattr(value, "content_type", "") or ""

    if (
        ext not in ALLOWED_AUDIO_EXTENSIONS
        and content_type not in ALLOWED_AUDIO_CONTENT_TYPES
    ):
        raise serializers.ValidationError(
            f"Noto'g'ri fayl formati. Ruxsat etilgan formatlar: "
            f"{', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}."
        )

    try:
        value.seek(0)
        audio = mutagen.File(value)
        value.seek(0)
        if audio is not None and audio.info is not None:
            duration = audio.info.length
            if duration > MAX_VOICE_DURATION_SECONDS:
                raise serializers.ValidationError(
                    f"Ovozli xabar davomiyligi 1 daqiqadan (60 soniya) oshmasligi kerak. "
                    f"Yuklangan fayl davomiyligi: {int(duration)} soniya."
                )
    except serializers.ValidationError:
        raise
    except Exception:
        pass

    return value


def validate_photo_limit(profile, max_photos=MAX_PHOTOS_PER_PROFILE):
    if profile is None:
        return

    from .models import ProfilePhoto

    current_count = ProfilePhoto.objects.filter(profile=profile, is_active=True).count()
    if current_count >= max_photos:
        raise serializers.ValidationError(
            {
                "image": (
                    f"Profilga maksimal {max_photos} ta rasm yuklash mumkin. "
                    "Yangi rasm qo'shish uchun avval bitta rasmni o'chiring."
                )
            }
        )


def validate_photo_face(image):
    if not image:
        return None
    is_valid, msg, embedding = verify_face_image(image)
    if not is_valid:
        raise serializers.ValidationError({"image": msg})
    return embedding


def validate_location(value):
    if not value or value == "string":
        return None
    if isinstance(value, str):
        try:
            from django.contrib.gis.geos import GEOSGeometry

            return GEOSGeometry(value)
        except Exception:
            return None
    return value
