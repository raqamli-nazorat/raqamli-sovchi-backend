import django_filters
from apps.core.base.filters import UUIDInFilter
from .models import User, UserPledge


class UserFilter(django_filters.FilterSet):
    auth_provider = django_filters.CharFilter(
        field_name="auth_provider", lookup_expr="exact"
    )
    role = django_filters.CharFilter(field_name="role", lookup_expr="exact")
    is_verified = django_filters.BooleanFilter(field_name="is_verified")
    start_date = django_filters.DateFilter(
        field_name="created_at", lookup_expr="gte", label="Yaratilgan vaqt (dan)"
    )
    end_date = django_filters.DateFilter(
        field_name="created_at", lookup_expr="lte", label="Yaratilgan vaqt (gacha)"
    )

    class Meta:
        model = User
        fields = ["auth_provider", "role", "is_verified", "start_date", "end_date"]


class UserPledgeFilter(django_filters.FilterSet):
    user = UUIDInFilter(field_name="user", lookup_expr="in")
    has_serious_badge = django_filters.BooleanFilter(field_name="has_serious_badge")

    class Meta:
        model = UserPledge
        fields = ["user", "has_serious_badge"]
