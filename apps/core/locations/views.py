from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.base.views import BaseManageViewSet

from .serializers import (
    RegionSerializer,
    DistrictSerializer
)
from .models import Region, District
from .filters import (
    RegionFilter,
    DistrictFilter
)


class RegionViewSet(BaseManageViewSet):
    queryset = Region.objects.active()
    serializer_class = RegionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = RegionFilter
    search_fields = ["name"]
    ordering_fields = ["created_at", "name"]


class DistrictViewSet(BaseManageViewSet):
    queryset = District.objects.select_related("region").active()
    serializer_class = DistrictSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DistrictFilter
    search_fields = ["name"]
    ordering_fields = ["created_at", "name"]