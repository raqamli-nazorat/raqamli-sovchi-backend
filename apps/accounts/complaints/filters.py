import django_filters

from .models import Complaint


class ComplaintFilter(django_filters.FilterSet):
    from_user = django_filters.UUIDFilter(field_name="from_user", lookup_expr="exact")
    to_user = django_filters.UUIDFilter(field_name="to_user", lookup_expr="exact")
    start_date = django_filters.IsoDateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
        label="Yaratilgan vaqt (dan) — YYYY-MM-DDTHH:mm:ss",
    )
    end_date = django_filters.IsoDateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
        label="Yaratilgan vaqt (gacha) — YYYY-MM-DDTHH:mm:ss",
    )

    class Meta:
        model = Complaint
        fields = ["status", "reason", "from_user", "to_user", "start_date", "end_date"]
