from rest_framework import serializers
from apps.core.base.serializers import BaseModelSerializer
from apps.core.utils.face import verify_face_image

from .models import Profile, ProfilePhoto, RepresentativeInfo
from .utils import can_view_profile_photos


class ProfilePhotoSerializer(BaseModelSerializer):
    class Meta:
        model = ProfilePhoto
        fields = "__all__"

    def validate(self, attrs):
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


class ProfileSerializer(BaseModelSerializer):
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


class ProfileMeSerializer(BaseModelSerializer):
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        loc = getattr(instance, "location", None)
        if loc is not None and hasattr(loc, "x"):
            ret["location"] = {
                "latitude": loc.y,
                "longitude": loc.x,
            }
        else:
            ret["location"] = instance.location_data
        return ret


class FaceVerificationSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True, label="Selfie rasm")
