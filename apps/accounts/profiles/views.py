from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.base.views import BaseManageViewSet

from .models import Profile, ProfilePhoto, RepresentativeInfo
from .serializers import (
    ProfileSerializer,
    ProfilePhotoSerializer,
    RepresentativeInfoSerializer,
)
from .filters import ProfileFilter


class ProfileViewSet(BaseManageViewSet):
    queryset = (
        Profile.objects.select_related("user", "region", "district")
        .prefetch_related("photos")
        .active()
    )
    serializer_class = ProfileSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProfileFilter
    search_fields = ["first_name", "last_name", "bio"]
    ordering_fields = ["created_at", "birth_year", "height", "weight"]


class ProfilePhotoViewSet(BaseManageViewSet):
    queryset = ProfilePhoto.objects.select_related("profile").active()
    serializer_class = ProfilePhotoSerializer
    ordering_fields = ["order", "created_at"]


class RepresentativeInfoViewSet(BaseManageViewSet):
    queryset = RepresentativeInfo.objects.select_related("profile").active()
    serializer_class = RepresentativeInfoSerializer
