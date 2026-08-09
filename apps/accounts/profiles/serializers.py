import os

from PIL import Image
from rest_framework import serializers

from apps.core.base.serializers import BaseModelSerializer
from apps.core.utils.face import verify_profile_photo

from .mixins import VoiceIntroValidationMixin
from .models import Profile, ProfilePhoto, RepresentativeInfo
from .utils import can_view_profile_photos


MAX_PROFILE_PHOTOS = 4
MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_PHOTO_DIMENSION = 4096
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_PHOTO_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
class ProfilePhotoSerializer(BaseModelSerializer):
    class Meta:
        model = ProfilePhoto
        fields = "__all__"
        extra_kwargs = {"profile": {"required": False}}

    def validate_image(self, value):
        extension = os.path.splitext(value.name)[1].lower()
        content_type = getattr(value, "content_type", None)
        if extension not in ALLOWED_PHOTO_EXTENSIONS:
            raise serializers.ValidationError(
                "Faqat JPG, PNG yoki WEBP rasm qabul qilinadi.", code="photo_type"
            )
        if content_type and content_type.lower() not in ALLOWED_PHOTO_MIME_TYPES:
            raise serializers.ValidationError(
                "Rasmning MIME turi qo'llab-quvvatlanmaydi.", code="photo_mime"
            )
        if value.size > MAX_PHOTO_BYTES:
            raise serializers.ValidationError(
                "Rasm 10 MB dan katta bo'lmasligi kerak.", code="photo_size"
            )
        try:
            with Image.open(value) as image:
                if (
                    image.width > MAX_PHOTO_DIMENSION
                    or image.height > MAX_PHOTO_DIMENSION
                ):
                    raise serializers.ValidationError(
                        "Rasm o'lchami 4096x4096 dan oshmasligi kerak.",
                        code="photo_dimensions",
                    )
        finally:
            value.seek(0)
        return value

    def validate_order(self, value):
        if not 1 <= value <= MAX_PROFILE_PHOTOS:
            raise serializers.ValidationError(
                "Rasm tartibi 1 dan 4 gacha bo'lishi kerak.", code="photo_order"
            )
        return value

    def validate(self, attrs):
        image = attrs.get("image")
        if image:
            is_valid, msg, embedding = verify_profile_photo(image)
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


class ProfileSerializer(VoiceIntroValidationMixin, BaseModelSerializer):
    compatibility_score = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Profile
        fields = "__all__"
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
        extra_kwargs = {"user": {"required": False}}

    def validate(self, attrs):
        candidate_type = attrs.get(
            "candidate_type", getattr(self.instance, "candidate_type", None)
        )
        gender = attrs.get("gender", getattr(self.instance, "gender", None))
        required_gender = {"groom": "male", "bride": "female"}.get(candidate_type)
        if required_gender and gender != required_gender:
            raise serializers.ValidationError(
                {"gender": "Nomzod turi bilan jins mos kelishi kerak."},
                code="candidate_gender_mismatch",
            )
        return super().validate(attrs)

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


class ProfileMeSerializer(VoiceIntroValidationMixin, BaseModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "id",
            "first_name",
            "last_name",
            "middle_name",
            "gender",
            "candidate_type",
            "birth_year",
            "height",
            "weight",
            "region",
            "district",
            "health_status",
            "marital_status",
            "education_level",
            "nationality",
            "profession",
            "has_children",
            "children_count",
            "expectations",
            "bio",
            "voice_intro",
            "latitude",
            "longitude",
            "location",
            "blur_photos",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
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

    def validate(self, attrs):
        candidate_type = attrs.get(
            "candidate_type", getattr(self.instance, "candidate_type", None)
        )
        gender = attrs.get("gender", getattr(self.instance, "gender", None))
        required_gender = {"groom": "male", "bride": "female"}.get(candidate_type)
        if required_gender and gender != required_gender:
            raise serializers.ValidationError(
                {"gender": "Nomzod turi bilan jins mos kelishi kerak."},
                code="candidate_gender_mismatch",
            )
        return super().validate(attrs)

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
