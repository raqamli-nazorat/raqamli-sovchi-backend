from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.base.views import BaseManageViewSet
from .models import EducationLevel, Nationality, Profession, MaritalStatus, HealthStatus
from .serializers import (
    EducationLevelSerializer,
    NationalitySerializer,
    ProfessionSerializer,
    MaritalStatusSerializer,
    HealthStatusSerializer,
)


class EducationLevelViewSet(BaseManageViewSet):
    queryset = EducationLevel.objects.active()
    serializer_class = EducationLevelSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]


class NationalityViewSet(BaseManageViewSet):
    queryset = Nationality.objects.active()
    serializer_class = NationalitySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]


class ProfessionViewSet(BaseManageViewSet):
    queryset = Profession.objects.active()
    serializer_class = ProfessionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]


class MaritalStatusViewSet(BaseManageViewSet):
    queryset = MaritalStatus.objects.active()
    serializer_class = MaritalStatusSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]


class HealthStatusViewSet(BaseManageViewSet):
    queryset = HealthStatus.objects.active()
    serializer_class = HealthStatusSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
