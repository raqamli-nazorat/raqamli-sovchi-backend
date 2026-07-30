from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from auditlog.models import LogEntry

from apps.core.base.views import BaseReadOnlyViewSet

from .serializers import LogEntrySerializer
from .filters import LogEntryFilter

class LogEntryViewSet(BaseReadOnlyViewSet):
    queryset = LogEntry.objects.select_related("actor", "content_type").all()
    serializer_class = LogEntrySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LogEntryFilter
    search_fields = ["object_repr", "changes", "actor__full_name", "remote_addr"]
    ordering_fields = ["timestamp", "action"]
    ordering = ["-timestamp"]
