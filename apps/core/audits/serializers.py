from rest_framework import serializers
from auditlog.models import LogEntry


class LogEntrySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(
        source="actor.full_name", read_only=True, default=None
    )
    content_type_name = serializers.CharField(
        source="content_type.name", read_only=True
    )

    class Meta:
        model = LogEntry
        fields = [
            "id",
            "action",
            "object_id",
            "object_pk",
            "object_repr",
            "content_type",
            "content_type_name",
            "actor",
            "actor_name",
            "remote_addr",
            "changes",
            "timestamp",
            "additional_data",
        ]
