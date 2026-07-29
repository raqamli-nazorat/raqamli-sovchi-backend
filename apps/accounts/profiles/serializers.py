from apps.core.base.serializers import BaseModelSerializer
from .models import Profile, ProfilePhoto, RepresentativeInfo


class ProfilePhotoSerializer(BaseModelSerializer):
    class Meta:
        model = ProfilePhoto
        fields = "__all__"


class RepresentativeInfoSerializer(BaseModelSerializer):
    class Meta:
        model = RepresentativeInfo
        fields = "__all__"


class ProfileSerializer(BaseModelSerializer):
    photos = ProfilePhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = "__all__"
        related_fields = {
            "user": ["id", "phone_number", "role"],
            "region": ["id", "name"],
            "district": ["id", "name"],
        }
