from rest_framework import serializers

from apps.core.base.serializers import BaseModelSerializer

from .models import Profile, ProfilePhoto, RepresentativeInfo, SavedProfile
from .utils import can_view_profile_photos
from .validators import (
    validate_location,
    validate_photo_face,
    validate_photo_limit,
    validate_voice_intro,
)


class SavedProfileSerializer(BaseModelSerializer):
    class Meta:
        model = SavedProfile
        fields = "__all__"
        related_fields = {
            "saved_profile": [
                "id",
                "first_name",
                "last_name",
                "gender",
                "birth_year",
                "height",
                "weight",
                "photos",
            ]
        }


class ProfilePhotoSerializer(BaseModelSerializer):
    class Meta:
        model = ProfilePhoto
        fields = "__all__"
        # profile so'rov yuboruvchining anketasidan olinadi (view: perform_create).
        # Mijoz uni yubora olsa, begona anketaga rasm biriktirib, 5 ta rasm
        # cheklovini ham chetlab o'tish mumkin edi.
        read_only_fields = ["profile"]

    def validate(self, attrs):
        request = self.context.get("request")

        if self.instance is None:
            profile = None
            if request and request.user.is_authenticated:
                profile = getattr(request.user, "profile", None)

            validate_photo_limit(profile)

        image = attrs.get("image")
        if image:
            embedding = validate_photo_face(image)
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
    is_saved = serializers.SerializerMethodField(read_only=True)
    has_answered_test = serializers.SerializerMethodField(read_only=True)
    answered_questions_count = serializers.SerializerMethodField(read_only=True)

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

        view = self.context.get("view")
        if view and getattr(view, "action", None) == "retrieve":
            request = self.context.get("request")
            if request and request.user and request.user.is_authenticated:
                user_profile = getattr(request.user, "profile", None)
                if user_profile and user_profile.id != obj.id:
                    from apps.accounts.questionnaire.services import (
                        calculate_compatibility_score,
                    )

                    return calculate_compatibility_score(user_profile, obj)

        return None

    def get_is_saved(self, obj):
        saved_ids = self.context.get("user_saved_profile_ids")
        if saved_ids is not None:
            return obj.id in saved_ids

        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False

        from .models import SavedProfile

        return SavedProfile.objects.filter(
            user=request.user, saved_profile=obj, is_active=True
        ).exists()

    def get_has_answered_test(self, obj):
        from apps.accounts.questionnaire.models import UserAnswer

        return UserAnswer.objects.filter(profile=obj, is_active=True).exists()

    def get_answered_questions_count(self, obj):
        from apps.accounts.questionnaire.models import UserAnswer

        return UserAnswer.objects.filter(profile=obj, is_active=True).count()

    def validate_voice_intro(self, value):
        return validate_voice_intro(value)

    def validate_location(self, value):
        return validate_location(value)

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


class RepresentativeConsentRequestSerializer(serializers.Serializer):
    """Vakil tomonidan nomzodga yuborilayotgan rozilik so'rovi uchun serialazer."""

    candidate_contact = serializers.CharField(
        help_text="Nomzodning telefon raqami (+998XXXXXXXXX) yoki email manzili"
    )
    # PrimaryKeyRelatedField o'rniga UUIDField — Kinship moduli import qilinmaydi,
    # service qatlami kinship_id ni o'zi DB dan topadi.
    kinship_id = serializers.UUIDField(required=False, allow_null=True)
    candidate_role = serializers.ChoiceField(
        choices=["groom", "bride"],
        default="groom",
    )

    def validate_candidate_contact(self, value):
        """Telefon raqam yoki email formatini tekshiradi."""
        import re

        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.core.validators import validate_email

        if re.match(r"^\+998\d{9}$", value):
            return value
        try:
            validate_email(value)
            return value
        except DjangoValidationError:
            raise serializers.ValidationError(
                "Noto'g'ri format. Telefon raqami (+998XXXXXXXXX) "
                "yoki to'g'ri email manzili kiritilishi kerak."
            )
