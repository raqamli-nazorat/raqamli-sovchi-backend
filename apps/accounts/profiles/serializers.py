from rest_framework import serializers
from apps.core.base.serializers import BaseModelSerializer

from .models import Profile, ProfilePhoto, RepresentativeInfo, SavedProfile
from .utils import can_view_profile_photos
from .validators import (
    validate_voice_intro,
    validate_photo_limit,
    validate_photo_face,
    validate_location,
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

    def validate(self, attrs):
        request = self.context.get("request")

        if self.instance is None:
            profile = attrs.get("profile")
            if profile is None and request and request.user.is_authenticated:
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
