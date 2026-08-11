import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.base.mixins import AutoSchemaMixin
from apps.core.base.views import BaseManageViewSet

from .filters import ProfileFilter
from .models import Profile, ProfilePhoto, RepresentativeInfo
from .permissions import ProfileMePermission, IsProfileOwnerOrStaff
from .serializers import (
    FaceVerificationSerializer,
    ProfilePhotoSerializer,
    ProfileSerializer,
    RepresentativeInfoSerializer,
)

logger = logging.getLogger(__name__)


class ProfileMeView(AutoSchemaMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [ProfileMePermission]
    serializer_class = ProfileSerializer

    def get_object(self):
        profile = (
            Profile.objects.select_related("user", "user__role", "region", "district")
            .prefetch_related("photos")
            .filter(user=self.request.user)
            .active()
            .first()
        )
        if not profile:
            raise NotFound("Foydalanuvchi profili topilmadi.")
        return profile


class ProfileViewSet(BaseManageViewSet):
    queryset = (
        Profile.objects.select_related("user", "user__role", "region", "district")
        .prefetch_related("photos")
        .active()
    )
    serializer_class = ProfileSerializer
    permission_classes = [IsProfileOwnerOrStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProfileFilter
    search_fields = ["first_name", "last_name", "bio"]
    ordering_fields = ["created_at", "birth_year", "height", "weight"]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        profiles_list = list(page) if page is not None else list(queryset)

        user_profile = (
            getattr(request.user, "profile", None)
            if request.user and request.user.is_authenticated
            else None
        )
        batch_scores = None

        if user_profile and profiles_list:
            from apps.accounts.questionnaire.services import (
                batch_calculate_compatibility_scores,
            )

            batch_scores = batch_calculate_compatibility_scores(
                user_profile, profiles_list
            )

        context = self.get_serializer_context()
        context["batch_compatibility_scores"] = batch_scores

        if page is not None:
            serializer = self.get_serializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context=context)
        return Response(serializer.data)

    def perform_create(self, serializer):
        from .services import create_profile

        target_user = create_profile(self.request.user, serializer.validated_data)
        serializer.save(user=target_user)

    def perform_update(self, serializer):
        from .services import update_profile

        update_profile(self.request.user, serializer.validated_data)
        serializer.save()


class ProfilePhotoViewSet(BaseManageViewSet):
    serializer_class = ProfilePhotoSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ["order", "created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = ProfilePhoto.objects.select_related("profile").active()
        if user.is_staff or user.is_superuser:
            return qs
        return qs.filter(profile__user=user)

    def perform_create(self, serializer):
        from .services import create_profile_photo

        profile = create_profile_photo(self.request.user, serializer.validated_data)
        if profile:
            serializer.save(profile=profile)
        else:
            serializer.save()


class RepresentativeInfoViewSet(BaseManageViewSet):
    queryset = RepresentativeInfo.objects.select_related("profile").active()
    serializer_class = RepresentativeInfoSerializer


class FaceVerificationView(AutoSchemaMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = FaceVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data["image"]

        from .services import verify_user_face

        status_code, result = verify_user_face(request.user, uploaded_file)
        return Response(result, status=status_code)
