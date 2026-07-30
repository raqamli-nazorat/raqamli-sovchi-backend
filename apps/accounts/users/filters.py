import django_filters
from apps.core.base.filters import UUIDInFilter, NumberInFilter
from .models import User, UserPledge, Role


class RoleFilter(django_filters.FilterSet):
    permissions = NumberInFilter(field_name="permissions", lookup_expr="in")
    start_date = django_filters.DateFilter(
        field_name="created_at", lookup_expr="gte", label="Yaratilgan vaqt (dan)"
    )
    end_date = django_filters.DateFilter(
        field_name="created_at", lookup_expr="lte", label="Yaratilgan vaqt (gacha)"
    )

    class Meta:
        model = Role
        fields = ["permissions", "start_date", "end_date"]


class UserFilter(django_filters.FilterSet):
    auth_provider = django_filters.CharFilter(
        field_name="auth_provider", lookup_expr="exact"
    )
    role = django_filters.CharFilter(field_name="role", lookup_expr="exact")
    candidate_type = django_filters.CharFilter(
        method="filter_candidate_type", label="Nomzod turi (Kuyov, Kelin, Vakil)"
    )
    region = django_filters.UUIDFilter(field_name="profile__region", lookup_expr="exact")
    is_verified = django_filters.BooleanFilter(field_name="is_verified")
    is_blocked = django_filters.BooleanFilter(field_name="is_blocked")
    is_active = django_filters.BooleanFilter(field_name="is_active")
    status = django_filters.CharFilter(method="filter_status", label="Status")
    start_date = django_filters.DateFilter(
        field_name="created_at", lookup_expr="gte", label="Created at (from)"
    )
    end_date = django_filters.DateFilter(
        field_name="created_at", lookup_expr="lte", label="Created at (to)"
    )

    class Meta:
        model = User
        fields = [
            "auth_provider",
            "role",
            "candidate_type",
            "region",
            "is_verified",
            "is_blocked",
            "is_active",
            "status",
            "start_date",
            "end_date",
        ]

    def filter_candidate_type(self, queryset, name, value):
        val_map = {
            "kuyov": "groom",
            "groom": "groom",
            "kelin": "bride",
            "bride": "bride",
            "vakil": "representative",
            "representative": "representative",
        }
        target = val_map.get(value.lower(), value)
        return queryset.filter(profile__candidate_type__iexact=target)

    def filter_status(self, queryset, name, value):
        val_map = {
            "bloklangan": "blocked",
            "blocked": "blocked",
            "tasdiqlangan": "approved",
            "approved": "approved",
            "anketa to'liq emas": "incomplete",
            "incomplete": "incomplete",
            "tekshiruvda": "review",
            "review": "review",
        }
        target = val_map.get(value.lower(), value)
        if target == "blocked":
            return queryset.filter(is_blocked=True)
        elif target == "approved":
            return queryset.filter(is_blocked=False, is_verified=True)
        elif target == "incomplete":
            return queryset.filter(is_blocked=False, is_verified=False, profile__isnull=True)
        elif target == "review":
            return queryset.filter(is_blocked=False, is_verified=False, profile__isnull=False)
        return queryset


class UserPledgeFilter(django_filters.FilterSet):
    user = UUIDInFilter(field_name="user", lookup_expr="in")
    has_serious_badge = django_filters.BooleanFilter(field_name="has_serious_badge")

    class Meta:
        model = UserPledge
        fields = ["user", "has_serious_badge"]
