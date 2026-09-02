from auditlog.models import LogEntry
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.base.views import BaseReadOnlyViewSet

from .filters import LogEntryFilter
from .serializers import LogEntrySerializer


class LogEntryViewSet(BaseReadOnlyViewSet):
    queryset = LogEntry.objects.select_related("actor", "content_type").all()
    serializer_class = LogEntrySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LogEntryFilter
    # User modelida full_name maydoni yo'q (u serializerda hisoblanadi),
    # shuning uchun qidiruv haqiqiy ustunlar bo'yicha olib boriladi.
    search_fields = [
        "object_repr",
        "changes",
        "actor__phone_number",
        "actor__email",
        "remote_addr",
    ]
    ordering_fields = ["timestamp", "action"]
    ordering = ["-timestamp"]
