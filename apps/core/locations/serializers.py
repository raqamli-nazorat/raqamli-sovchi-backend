from apps.core.base.serializers import BaseModelSerializer

from .models import Region, District


class RegionSerializer(BaseModelSerializer):
    class Meta:
        model = Region
        fields = "__all__"


class DistrictSerializer(BaseModelSerializer):
    class Meta:
        model = District
        fields = "__all__"

        related_fields = {"region": ["id", "name"]}
