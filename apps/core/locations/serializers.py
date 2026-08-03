from rest_framework import serializers

from apps.core.base.serializers import BaseModelSerializer
from .models import Region, District


class RegionSerializer(BaseModelSerializer):
    count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Region
        fields = "__all__"

    def get_count(self, obj):
        return obj.districts.count()


class DistrictSerializer(BaseModelSerializer):
    class Meta:
        model = District
        fields = "__all__"

        related_fields = {"region": ["id", "name"]}
