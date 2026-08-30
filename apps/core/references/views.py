from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.base.views import BaseManageViewSet

from .models import (
    EducationLevel,
    HealthStatus,
    Kinship,
    MaritalStatus,
    Nationality,
    Profession,
)
from .serializers import (
    EducationLevelSerializer,
    HealthStatusSerializer,
    KinshipSerializer,
    MaritalStatusSerializer,
    NationalitySerializer,
    ProfessionSerializer,
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


class KinshipViewSet(BaseManageViewSet):
    queryset = Kinship.objects.active()
    serializer_class = KinshipSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
