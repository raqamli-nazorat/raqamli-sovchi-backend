import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.decorators import action
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
from .services import (
    approve_representative_consent,
    create_profile,
    create_profile_photo,
    get_nearby_profiles,
    reject_representative_consent,
    send_representative_consent_request,
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
    ordering_fields = ["created_at", "birth_year", "height", "weight"]

    def get_queryset(self):
        qs = (
            Profile.objects.select_related("user", "user__role", "region", "district")
            .prefetch_related("photos")
            .active()
        )
        user = self.request.user

        if user and user.is_authenticated and not (user.is_staff or user.is_superuser or bool(user.role and not user.role.is_default)):
            from apps.accounts.users.models import BlockedUser

            blocked_user_ids = set(
                BlockedUser.objects.filter(blocker=user).values_list(
                    "blocked_id", flat=True
                )
            )
            blocked_by_user_ids = set(
                BlockedUser.objects.filter(blocked=user).values_list(
                    "blocker_id", flat=True
                )
            )
            all_blocked = blocked_user_ids | blocked_by_user_ids
            if all_blocked:
                qs = qs.exclude(user_id__in=all_blocked)

        return qs

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

        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)

        profiles_list = list(page) if page is not None else list(qs)

        batch_scores = None
        if profiles_list:
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

        serializer = self.get_serializer(qs, many=True, context=context)
        return Response(serializer.data)


class ProfilePhotoViewSet(BaseManageViewSet):
    serializer_class = ProfilePhotoSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ["order", "created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = ProfilePhoto.objects.select_related("profile").active()

        if user.is_staff or user.is_superuser or bool(user.role and not user.role.is_default):
            return qs
        return qs.filter(profile__user=user)

    def perform_create(self, serializer):
        profile = create_profile_photo(self.request.user, serializer.validated_data)
        if profile:
            serializer.save(profile=profile)
        else:
            serializer.save()


class RepresentativeInfoViewSet(BaseManageViewSet):
    queryset = RepresentativeInfo.objects.select_related(
        "profile", "target_candidate"
    ).active()
    serializer_class = RepresentativeInfoSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="send-consent-request")
    def send_consent_request(self, request):
        candidate_contact = request.data.get("candidate_contact")
        kinship_id = request.data.get("kinship_id")
        candidate_role = request.data.get("candidate_role", "groom")

        rep_info, target_user = send_representative_consent_request(
            request.user, candidate_contact, kinship_id, candidate_role
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
