import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.base.mixins import AutoSchemaMixin
from apps.core.base.views import BaseManageViewSet
from apps.core.utils.face import (
    _save_as_rgb_jpeg,
    _temp_jpeg_files,
    check_against_blocked_faces,
    extract_embedding,
    hash_compare,
    register_user_faces_as_blocked,
)

from .filters import ProfileFilter
from .models import Profile, ProfilePhoto, RepresentativeInfo
from .serializers import (
    FaceVerificationSerializer,
    ProfileMeSerializer,
    ProfilePhotoSerializer,
    ProfileSerializer,
    RepresentativeInfoSerializer,
)

logger = logging.getLogger(__name__)


class ProfileMeView(AutoSchemaMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileMeSerializer

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

    def perform_destroy(self, instance):
        logger.warning(
            "Profil o'chirildi (soft-delete): ProfileID=%s | UserID=%s",
            instance.id,
            instance.user_id,
        )
        instance.delete()


class ProfileViewSet(BaseManageViewSet):
    queryset = (
        Profile.objects.select_related("user", "user__role", "region", "district")
        .prefetch_related("photos")
        .active()
    )
    serializer_class = ProfileSerializer
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

            batch_scores = batch_calculate_compatibility_scores(user_profile, profiles_list)

        context = self.get_serializer_context()
        context["batch_compatibility_scores"] = batch_scores

        if page is not None:
            serializer = self.get_serializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context=context)
        return Response(serializer.data)

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
        profile = getattr(self.request.user, "profile", None)
        if profile and not serializer.validated_data.get("profile"):
            photo = serializer.save(profile=profile)
        else:
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

        try:
            uploaded_file.seek(0)
        except Exception:
            pass

        with _temp_jpeg_files(f"verify_probe_{user.id}") as (temp_path,):
            try:
                _save_as_rgb_jpeg(uploaded_file, temp_path)
                probe_emb = extract_embedding(temp_path)
                if probe_emb:
                    is_blocked_match, bf_obj, dist = check_against_blocked_faces(
                        probe_emb
                    )
                    if is_blocked_match:
                        logger.warning(
                            "Bloklangan shaxs yuzi aniqlandi! Yangi hisob ham bloklanmoqda: UserID=%s | Distance=%.4f",
                            user.id,
                            dist,
                        )
                        user.is_blocked = True
                        user.save(update_fields=["is_blocked"])
                        register_user_faces_as_blocked(
                            user,
                            reason="Bloklangan shaxs yuzi bilan yangi hisob ochishga urinish",
                            embedding=probe_emb,
                        )
                        return Response(
                            {
                                "detail": "Ushbu yuz egasiga tegishli bloklangan hisob aniqlandi! Tizimdan foydalanish taqiqlanadi va ushbu hisobingiz ham bloklandi.",
                                "verified": False,
                                "is_blocked": True,
                            },
                            status=status.HTTP_403_FORBIDDEN,
                        )
            except Exception as e:
                logger.warning("Bloklangan yuz tekshiruvida xatolik: %s", e)

        try:
            uploaded_file.seek(0)
        except Exception:
            pass

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
