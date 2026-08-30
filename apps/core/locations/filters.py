import django_filters

from apps.core.base.filters import UUIDInFilter

from .models import District, Region


class RegionFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(
        field_name="created_at", lookup_expr="gte", label="Yaratilgan vaqt (dan)"
    )
    end_date = django_filters.DateFilter(
        field_name="created_at", lookup_expr="lte", label="Yaratilgan vaqt (gacha)"
    )

    class Meta:
        model = Region
        fields = ["start_date", "end_date"]


class DistrictFilter(django_filters.FilterSet):
    region = UUIDInFilter(field_name="region", lookup_expr="in")
    start_date = django_filters.DateFilter(
        field_name="created_at", lookup_expr="gte", label="Yaratilgan vaqt (dan)"
    )
    end_date = django_filters.DateFilter(
        field_name="created_at", lookup_expr="lte", label="Yaratilgan vaqt (gacha)"
    )

    class Meta:
        model = District
        fields = ["region", "start_date", "end_date"]
