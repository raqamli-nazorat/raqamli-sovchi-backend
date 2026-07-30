import django_filters
from apps.core.base.filters import UUIDInFilter
from .models import Profile, ProfilePhoto


class ProfileFilter(django_filters.FilterSet):
    region = UUIDInFilter(field_name="region", lookup_expr="in")
    district = UUIDInFilter(field_name="district", lookup_expr="in")
    role = django_filters.CharFilter(field_name="role", lookup_expr="exact")
    gender = django_filters.CharFilter(field_name="gender", lookup_expr="exact")
    health_status = django_filters.CharFilter(
        field_name="health_status", lookup_expr="exact"
    )
    marital_status = django_filters.CharFilter(
        field_name="marital_status", lookup_expr="exact"
    )

    height_min = django_filters.NumberFilter(field_name="height", lookup_expr="gte")
    height_max = django_filters.NumberFilter(field_name="height", lookup_expr="lte")

    weight_min = django_filters.NumberFilter(field_name="weight", lookup_expr="gte")
    weight_max = django_filters.NumberFilter(field_name="weight", lookup_expr="lte")

    birth_year_min = django_filters.NumberFilter(
        field_name="birth_year", lookup_expr="gte"
    )
    birth_year_max = django_filters.NumberFilter(
        field_name="birth_year", lookup_expr="lte"
    )

    class Meta:
        model = Profile
        fields = [
            "role",
            "gender",
            "region",
            "district",
            "health_status",
            "marital_status",
            "height_min",
            "height_max",
            "weight_min",
            "weight_max",
            "birth_year_min",
            "birth_year_max",
        ]
