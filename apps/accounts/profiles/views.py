import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.base.mixins import AutoSchemaMixin
from apps.core.base.views import BaseManageViewSet

from .filters import ProfileFilter
from .models import Profile, ProfilePhoto, RepresentativeInfo
from .permissions import IsProfileOwnerOrStaff, ProfileMePermission
from .serializers import (
    FaceVerificationSerializer,
    ProfilePhotoSerializer,
    ProfileSerializer,
    RepresentativeInfoSerializer,
    SavedProfileSerializer,
)
from .services import (
    approve_representative_consent,
    create_profile,
    create_profile_photo,
    filter_profiles_for_user,
    get_nearby_profiles,
    get_paginated_profiles_response,
    get_saved_profile_objects_for_user,
    get_saved_profiles_for_user,
    reject_representative_consent,
    save_profile_for_user,
    send_representative_consent_request,
    unsave_profile_for_user,
    update_profile,
    verify_user_face,
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
    serializer_class = ProfileSerializer
    permission_classes = [IsProfileOwnerOrStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProfileFilter
    search_fields = ["first_name", "last_name", "bio"]
    ordering_fields = ["created_at", "birth_date", "height", "weight"]

    def get_queryset(self):
        qs = (
            Profile.objects.select_related(
                "user",
                "user__role",
                "region",
                "district",
                # Serializer bu ma'lumotnomalarni ham ochadi (related_fields),
                # shuning uchun ular ham select_related ga kiritiladi — aks holda
                # har bir profil uchun alohida so'rov ketadi (N+1).
                "education_level",
                "nationality",
                "profession",
                "health_status",
                "marital_status",
            )
            .prefetch_related("photos")
            .active()
        )
        return filter_profiles_for_user(qs, self.request.user)

    def perform_create(self, serializer):
        target_user = create_profile(self.request.user, serializer.validated_data)
        serializer.save(user=target_user)

    def perform_update(self, serializer):
        update_profile(self.request.user, serializer.validated_data)
        serializer.save()

    @action(
        detail=False,
        methods=["get"],
        url_path="nearby",
        permission_classes=[permissions.IsAuthenticated],
    )
    def nearby(self, request):
        try:
            radius_km = float(request.query_params.get("radius", 10))
        except (ValueError, TypeError):
            radius_km = 10.0

        try:
            user_profile, qs = get_nearby_profiles(
                request.user, self.get_queryset(), radius_km=radius_km
            )
        except Exception as err:
            if hasattr(err, "detail"):
                return Response(err.detail, status=status.HTTP_400_BAD_REQUEST)
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="matches",
        permission_classes=[permissions.IsAuthenticated],
    )
    def matches(self, request):
        return get_paginated_profiles_response(
            self, request, self.get_queryset(), only_matched=True
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="save",
        permission_classes=[permissions.IsAuthenticated],
    )
    def save_profile(self, request, pk=None):
        saved_obj = save_profile_for_user(request.user, pk)
        return Response(
            {
                "message": "Anketa saqlanganlarga qo'shildi.",
                "is_saved": True,
                "saved_id": str(saved_obj.id),
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path="unsave",
        permission_classes=[permissions.IsAuthenticated],
    )
    def unsave_profile(self, request, pk=None):
        unsave_profile_for_user(request.user, pk)
        return Response(
            {
                "message": "Anketa saqlanganlardan olib tashlandi.",
                "is_saved": False,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="saved",
        permission_classes=[permissions.IsAuthenticated],
    )
    def saved(self, request):
        qs, saved_profile_ids = get_saved_profiles_for_user(request.user)
        return get_paginated_profiles_response(
            self,
            request,
            qs,
            extra_context={"user_saved_profile_ids": saved_profile_ids},
        )


class ProfilePhotoViewSet(BaseManageViewSet):
    serializer_class = ProfilePhotoSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ["order", "created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = ProfilePhoto.objects.select_related("profile").active()

        if (
            user.is_staff
            or user.is_superuser
            or bool(user.role and not user.role.is_default)
        ):
            return qs
        return qs.filter(profile__user=user)

    def perform_create(self, serializer):
        profile = create_profile_photo(self.request.user, serializer.validated_data)
        if not profile:
            raise ValidationError(
                "Rasm yuklash uchun avval o'z anketangizni to'ldirishingiz kerak."
            )
        serializer.save(profile=profile)


class RepresentativeInfoViewSet(BaseManageViewSet):
    queryset = RepresentativeInfo.objects.select_related(
        "profile", "target_candidate"
    ).active()
    serializer_class = RepresentativeInfoSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="send-consent-request")
    def send_consent_request(self, request):
        from .serializers import RepresentativeConsentRequestSerializer

        serializer = RepresentativeConsentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        rep_info, target_user = send_representative_consent_request(
            request.user,
            data["candidate_contact"],
            data.get("kinship_id"),
            data["candidate_role"],
        )

        return Response(
            {
                "message": "Rozilik so'rovi yuborildi.",
                "is_target_registered": bool(target_user),
                "rep_info_id": str(rep_info.id),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="approve-consent")
    def approve_consent(self, request):
        rep_info_id = request.data.get("rep_info_id")

        approve_representative_consent(request.user, rep_info_id)

        return Response(
            {
                "message": "Rozilik berildi. Vakillik biriktirildi.",
                "is_approved": True,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="reject-consent")
    def reject_consent(self, request):
        rep_info_id = request.data.get("rep_info_id")

        reject_representative_consent(request.user, rep_info_id)

        return Response(
            {"message": "Vakillik so'rovi rad etildi va o'chirildi."},
            status=status.HTTP_200_OK,
        )


class FaceVerificationView(AutoSchemaMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = FaceVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data["image"]

        status_code, result = verify_user_face(request.user, uploaded_file)
        return Response(result, status=status_code)


class SavedProfileViewSet(BaseManageViewSet):
    serializer_class = SavedProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return get_saved_profile_objects_for_user(self.request.user)

    def perform_create(self, serializer):
        saved_profile = serializer.validated_data.get("saved_profile")
        if saved_profile:
            saved_obj = save_profile_for_user(self.request.user, saved_profile.id)
            serializer.instance = saved_obj
        else:
            serializer.save(user=self.request.user)
