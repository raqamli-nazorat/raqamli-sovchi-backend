from rest_framework import serializers
from apps.core.base.serializers import BaseModelSerializer
from apps.core.utils.face import verify_face_image

from .models import Profile, ProfilePhoto, RepresentativeInfo


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


class RepresentativeInfoSerializer(BaseModelSerializer):
    class Meta:
        model = RepresentativeInfo
        fields = "__all__"


class ProfileSerializer(BaseModelSerializer):
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
                "is_staff",
                "created_at",
            ],
            "region": ["id", "name"],
            "district": ["id", "name"],
            "photos": ["id", "image", "is_main", "order", "created_at"],
        }


class FaceVerificationSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True, label="Selfie rasm")
