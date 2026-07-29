import django_filters
from auditlog.models import LogEntry
from apps.core.base.filters import UUIDInFilter, NumberInFilter


class LogEntryFilter(django_filters.FilterSet):
    actor = UUIDInFilter(field_name="actor_id", lookup_expr="in")
    content_type = NumberInFilter(field_name="content_type_id", lookup_expr="in")
    action = django_filters.ChoiceFilter(choices=LogEntry.Action.choices)

    start_date = django_filters.DateFilter(
        field_name="timestamp", lookup_expr="gte", label="Vaqt (dan)"
    )
    end_date = django_filters.DateFilter(
        field_name="timestamp", lookup_expr="lte", label="Vaqt (gacha)"
    )

    class Meta:
        model = LogEntry
        fields = [
            "actor",
            "content_type",
            "action",
            "object_id",
            "start_date",
            "end_date",
        ]
