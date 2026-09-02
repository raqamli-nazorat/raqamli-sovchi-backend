from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.base.views import BaseManageViewSet

from .filters import DistrictFilter, RegionFilter
from .models import District, Region
from .serializers import DistrictSerializer, RegionSerializer


class RegionViewSet(BaseManageViewSet):
    queryset = Region.objects.prefetch_related("districts").active()
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
