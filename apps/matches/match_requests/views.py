from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.base.views import BaseManageViewSet
from .models import MatchRequest
from .serializers import MatchRequestSerializer


class MatchRequestViewSet(BaseManageViewSet):
    queryset = MatchRequest.objects.select_related(
        "from_profile", "to_profile", "question"
    ).active()
    serializer_class = MatchRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "from_profile", "to_profile"]
    ordering_fields = ["created_at"]
