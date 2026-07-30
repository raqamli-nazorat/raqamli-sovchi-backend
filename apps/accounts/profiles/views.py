import logging
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.base.views import BaseManageViewSet
from apps.core.base.mixins import AutoSchemaMixin
from apps.core.utils.face import hash_compare

from .models import Profile, ProfilePhoto, RepresentativeInfo
from .serializers import (
    ProfileSerializer,
    ProfilePhotoSerializer,
    RepresentativeInfoSerializer,
    FaceVerificationSerializer,
)
from .filters import ProfileFilter

logger = logging.getLogger(__name__)

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

    def perform_create(self, serializer):
        profile = serializer.save()
        logger.info(
            "Yangi profil yaratildi: ProfileID=%s | UserID=%s",
            profile.id,
            profile.user_id,
        )

    def perform_update(self, serializer):
        profile = serializer.save()
        logger.info(
            "Profil yangilandi: ProfileID=%s | UserID=%s", profile.id, profile.user_id
        )

    def perform_destroy(self, instance):
        logger.warning(
            "Profil o'chirildi (soft-delete): ProfileID=%s | UserID=%s",
            instance.id,
            instance.user_id,
        )
        instance.delete()

class ProfilePhotoViewSet(BaseManageViewSet):
    queryset = ProfilePhoto.objects.select_related("profile").active()
    serializer_class = ProfilePhotoSerializer
    ordering_fields = ["order", "created_at"]

    def perform_create(self, serializer):
        photo = serializer.save()
        logger.info(
            "Profil rasmi yuklandi: PhotoID=%s | ProfileID=%s",
            photo.id,
            photo.profile_id,
        )

    def perform_update(self, serializer):
        photo = serializer.save()
        logger.info(
            "Profil rasmi yangilandi: PhotoID=%s | ProfileID=%s",
            photo.id,
            photo.profile_id,
        )

    def perform_destroy(self, instance):
        logger.warning(
            "Profil rasmi o'chirildi: PhotoID=%s | ProfileID=%s",
            instance.id,
            instance.profile_id,
        )
        instance.delete()

class RepresentativeInfoViewSet(BaseManageViewSet):
    queryset = RepresentativeInfo.objects.select_related("profile").active()
    serializer_class = RepresentativeInfoSerializer

    def perform_create(self, serializer):
        rep_info = serializer.save()
        logger.info(
            "Vakil ma'lumoti yaratildi: RepInfoID=%s | ProfileID=%s",
            rep_info.id,
            rep_info.profile_id,
        )

    def perform_update(self, serializer):
        rep_info = serializer.save()
        logger.info(
            "Vakil ma'lumoti yangilandi: RepInfoID=%s | ProfileID=%s",
            rep_info.id,
            rep_info.profile_id,
        )

    def perform_destroy(self, instance):
        logger.warning(
            "Vakil ma'lumoti o'chirildi: RepInfoID=%s | ProfileID=%s",
            instance.id,
            instance.profile_id,
        )
        instance.delete()

class FaceVerificationView(AutoSchemaMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        logger.info("Yuz tekshiruvi so'rovi kelib tushdi: UserID=%s", user.id)

        serializer = FaceVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Yuz tekshiruvi validatsiya xatosi: UserID=%s | Errors=%s",
                user.id,
                serializer.errors,
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data["image"]

        profile = getattr(user, "profile", None)
        if not profile:
            logger.warning(
                "Yuz tekshiruvi xatosi: Profil yaratilmagan. UserID=%s", user.id
            )
            return Response(
                {"detail": "Foydalanuvchi profili mavjud emas. Avval profil yarating!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_verified, msg = hash_compare(profile, uploaded_file)

        if is_verified:
            logger.info("Yuz tekshiruvi MUVAFFAQIYATLI: UserID=%s", user.id)
            return Response(
                {"message": msg, "verified": True}, status=status.HTTP_200_OK
            )

        logger.warning(
            "Yuz tekshiruvi DIQQAT (Muvaffaqiyatsiz): UserID=%s | Sabab=%s",
            user.id,
            msg,
        )
        return Response(
            {"detail": msg, "verified": False}, status=status.HTTP_400_BAD_REQUEST
        )
