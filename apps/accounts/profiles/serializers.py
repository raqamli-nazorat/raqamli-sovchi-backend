import os
import mutagen
from rest_framework import serializers
from apps.core.base.serializers import BaseModelSerializer
from apps.core.utils.face import verify_face_image

from .models import Profile, ProfilePhoto, RepresentativeInfo
from .utils import can_view_profile_photos

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


def _validate_voice_intro(value):
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


MAX_PHOTOS_PER_PROFILE = 5


class ProfilePhotoSerializer(BaseModelSerializer):
    class Meta:
        model = ProfilePhoto
        fields = "__all__"

    def validate(self, attrs):
        request = self.context.get("request")

        if self.instance is None:
            profile = attrs.get("profile")
            if profile is None and request and request.user.is_authenticated:
                profile = getattr(request.user, "profile", None)

            if profile is not None:
                current_count = ProfilePhoto.objects.filter(
                    profile=profile, is_active=True
                ).count()
                if current_count >= MAX_PHOTOS_PER_PROFILE:
                    raise serializers.ValidationError(
                        {
                            "image": (
                                f"Profilga maksimal {MAX_PHOTOS_PER_PROFILE} ta rasm yuklash mumkin. "
                                "Yangi rasm qo'shish uchun avval bitta rasmni o'chiring."
                            )
                        }
                    )

        image = attrs.get("image")
        if image:
            is_valid, msg, embedding = verify_face_image(image)
            if not is_valid:
                raise serializers.ValidationError({"image": msg})
            if embedding:
                attrs["embedding"] = embedding

        return super().validate(attrs)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get("request")
        user = request.user if request else None

        if instance.profile and not can_view_profile_photos(user, instance.profile):
            ret["image"] = None

        return ret


class RepresentativeInfoSerializer(BaseModelSerializer):
    class Meta:
        model = RepresentativeInfo
        fields = "__all__"
        related_fields = {
            "kinship": ["id", "name"],
        }


class ProfileSerializer(BaseModelSerializer):
    compatibility_score = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Profile
        fields = "__all__"
        extra_kwargs = {
            "user": {"required": False, "allow_null": True},
        }
        related_fields = {
            "user": [
                "id",
                "phone_number",
                "email",
                "auth_provider",
                "is_verified",
                "created_at",
            ],
            "region": ["id", "name"],
            "district": ["id", "name"],
            "education_level": ["id", "name"],
            "nationality": ["id", "name"],
            "profession": ["id", "name"],
            "health_status": ["id", "name"],
            "marital_status": ["id", "name"],
            "photos": ["id", "image", "is_main", "order", "created_at"],
        }

    def get_compatibility_score(self, obj):
        batch_scores = self.context.get("batch_compatibility_scores")
        if batch_scores is not None:
            return batch_scores.get(obj.id)

        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return None

        user_profile = getattr(request.user, "profile", None)
        if not user_profile or user_profile.id == obj.id:
            return None

        from apps.accounts.questionnaire.services import calculate_compatibility_score

        return calculate_compatibility_score(user_profile, obj)

    def validate_voice_intro(self, value):
        return _validate_voice_intro(value)

    def validate_location(self, value):
        if not value or value == "string":
            return None
        if isinstance(value, str):
            try:
                from django.contrib.gis.geos import GEOSGeometry

                return GEOSGeometry(value)
            except Exception:
                return None
        return value

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.location:
            ret["location"] = {
                "latitude": instance.location.y,
                "longitude": instance.location.x,
            }
        else:
            ret["location"] = None
        return ret


class FaceVerificationSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True, label="Selfie rasm")
