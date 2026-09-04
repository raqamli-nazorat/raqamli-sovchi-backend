import hashlib

from django.contrib.auth.models import Permission
from django.db.models import Count, IntegerField, OuterRef, Subquery
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics, permissions, status, views
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.base.mixins import AutoSchemaMixin
from apps.core.base.views import BaseManageViewSet, BaseReadOnlyViewSet
from apps.core.utils.throttles import CustomScopedRateThrottle

from .admin_serializers import (
    AdminUserBlockSerializer,
    AdminUserComplaintSerializer,
    AdminUserDetailSerializer,
    AdminUserHistorySerializer,
    AdminUserListSerializer,
    AdminUserMatchHistorySerializer,
    build_user_history,
)
from .filters import RoleFilter, UserFilter, UserPledgeFilter
from .models import BlockedUser, Role, User, UserDevice, UserPledge
from .serializers import (
    BlockedUserSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    EmailAuthSerializer,
    GoogleLoginSerializer,
    PermissionSerializer,
    PhoneAuthSerializer,
    RoleSerializer,
    UserDeviceSerializer,
    UserPledgeSerializer,
    UserSerializer,
)

# Qurilma sarlavhalari. Kirish paytida yuborilsa, qurilma ro'yxatga olinadi va
# uning identifikatori JWT ichiga yoziladi — keyinchalik seansni masofadan
# bekor qilish shu orqali ishlaydi. Sxemada e'lon qilinmasa, Swagger'dan
# yuborib bo'lmaydi.
DEVICE_HEADER_PARAMETERS = [
    OpenApiParameter(
        name="X-Device-Id",
        type=str,
        location=OpenApiParameter.HEADER,
        required=False,
        description="Qurilmaning noyob identifikatori",
    ),
    OpenApiParameter(
        name="X-Device-Name",
        type=str,
        location=OpenApiParameter.HEADER,
        required=False,
        description="Qurilma nomi (masalan: Samsung S23)",
    ),
    OpenApiParameter(
        name="X-Device-OS",
        type=str,
        location=OpenApiParameter.HEADER,
        required=False,
        description="Qurilma operatsion tizimi (masalan: Android 14)",
    ),
]


class PermissionViewSet(BaseReadOnlyViewSet):
    queryset = Permission.objects.select_related("content_type").exclude(
        content_type__app_label__in=[
            "admin",
            "auth",
            "sessions",
            "contenttypes",
            "django_celery_beat",
        ]
    )
    serializer_class = PermissionSerializer
    pagination_class = None

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        grouped_data = {}
        for perm in serializer.data:
            group_key = perm["model_name"]

            if group_key not in grouped_data:
                grouped_data[group_key] = {
                    "model_name": perm["model_name"],
                    "group_label": perm["group_label"],
                    "permissions": [],
                }

            grouped_data[group_key]["permissions"].append(
                {
                    "id": perm["id"],
                    "name": perm["name"],
                    "codename": perm["codename"],
                    "model_name": perm["model_name"],
                    "group_label": perm["group_label"],
                }
            )

        return Response(grouped_data)


class RoleViewSet(BaseManageViewSet):
    queryset = Role.objects.active()
    serializer_class = RoleSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = RoleFilter
    search_fields = ["name"]
    ordering_fields = ["created_at", "name"]

    def get_queryset(self):
        qs = super().get_queryset()

        perms_subq = (
            Role.permissions.through.objects.filter(role_id=OuterRef("pk"))
            .values("role_id")
            .annotate(c=Count("permission_id"))
            .values("c")
        )

        qs = qs.annotate(
            permissions_count=Subquery(perms_subq, output_field=IntegerField())
        )

        if self.action != "list":
            qs = qs.prefetch_related("permissions")
        return qs

    @property
    def serializer_fields(self):
        if self.action == "list":
            return [
                "id",
                "name",
                "is_default",
                "permissions_count",
                "created_at",
                "updated_at",
            ]
        return None


class UserMeView(AutoSchemaMixin, generics.RetrieveDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="region",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="Viloyat UUID si bo'yicha filtrlash.",
        ),
        OpenApiParameter(
            name="district",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="Tuman UUID si bo'yicha filtrlash.",
        ),
        OpenApiParameter(
            name="role",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="Rol UUID si bo'yicha filtrlash.",
        ),
        OpenApiParameter(
            name="candidate_type",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Nomzod turi bo'yicha filtrlash.",
            enum=["groom", "bride", "representative"],
        ),
        OpenApiParameter(
            name="auth_provider",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Ro'yxatdan o'tgan usul bo'yicha filtrlash.",
            enum=["phone", "telegram", "google", "email"],
        ),
        OpenApiParameter(
            name="status",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Foydalanuvchi holati bo'yicha filtrlash.",
            enum=["tasdiqlangan", "tekshiruvda", "bloklangan", "anketa to'liq emas"],
        ),
        OpenApiParameter(
            name="has_representative",
            type=bool,
            location=OpenApiParameter.QUERY,
            description="true — vakili biriktirilgan nomzodlar; false — vakili yo'qlar.",
        ),
        OpenApiParameter(
            name="start_date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Yaratilgan sana (dan). Format: YYYY-MM-DD.",
        ),
        OpenApiParameter(
            name="end_date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Yaratilgan sana (gacha). Format: YYYY-MM-DD.",
        ),
        OpenApiParameter(
            name="updated_start_date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Yangilangan sana (dan). Format: YYYY-MM-DD.",
        ),
        OpenApiParameter(
            name="updated_end_date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Yangilangan sana (gacha). Format: YYYY-MM-DD.",
        ),
    ]
)
class UserViewSet(BaseManageViewSet):
    queryset = (
        User.objects.select_related(
            "profile", "profile__region", "profile__district", "role"
        )
        .prefetch_related("profile__photos")
        .active()
    )
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = [
        "phone_number",
        "email",
        "profile__first_name",
        "profile__last_name",
    ]
    ordering_fields = ["created_at", "phone_number"]

    def get_serializer_class(self):
        """Action ga qarab kerakli serializer sinfini qaytaradi."""
        if self.action == "list":
            return AdminUserListSerializer
        if self.action == "retrieve":
            return AdminUserDetailSerializer
        if self.action == "block_user":
            return AdminUserBlockSerializer
        return UserSerializer

    def get_queryset(self):
        """Action ga qarab optimallashtirilgan queryset qaytaradi."""
        if self.action == "retrieve":
            from django.db.models import Prefetch

            from apps.accounts.profiles.models import RepresentativeInfo
            from apps.accounts.questionnaire.models import UserAnswer

            return (
                User.objects.select_related(
                    "profile",
                    "profile__region",
                    "profile__district",
                    "profile__nationality",
                    "profile__profession",
                    "profile__education_level",
                    "profile__marital_status",
                    "profile__health_status",
                    "role",
                )
                .prefetch_related(
                    "profile__photos",
                    Prefetch(
                        "profile__answers",
                        queryset=UserAnswer.objects.filter(
                            is_active=True
                        ).select_related("question__section", "selected_option"),
                    ),
                    Prefetch(
                        "represented_by_infos",
                        queryset=RepresentativeInfo.objects.filter(is_active=True)
                        .select_related(
                            "profile__user",
                            "profile__region",
                            "profile__district",
                            "kinship",
                        )
                        .prefetch_related(
                            "profile__representative_infos",
                            Prefetch(
                                "profile__answers",
                                queryset=UserAnswer.objects.filter(
                                    is_active=True
                                ).order_by("-created_at"),
                            ),
                        )
                        .order_by("-created_at"),
                    ),
                )
                .active()
            )

        if self.action == "list":
            from apps.accounts.questionnaire.models import UserAnswer

            answered_subq = (
                UserAnswer.objects.filter(profile__user=OuterRef("pk"), is_active=True)
                .values("profile__user")
                .annotate(c=Count("id"))
                .values("c")
            )
            return (
                User.objects.select_related(
                    "profile", "profile__region", "profile__district", "role"
                )
                .prefetch_related("profile__photos")
                .annotate(
                    answered_count=Subquery(answered_subq, output_field=IntegerField())
                )
                .active()
                .order_by("-created_at")
            )

        return (
            User.objects.select_related(
                "profile", "profile__region", "profile__district", "role"
            )
            .prefetch_related("profile__photos")
            .active()
        )

    def get_serializer_context(self):
        """List action uchun context'ga total_questions qo'shadi."""
        context = super().get_serializer_context()
        if self.action == "list":
            from apps.accounts.questionnaire.models import Question

            context["total_questions"] = Question.objects.filter(is_active=True).count()
        return context

    @extend_schema(
        summary="Foydalanuvchini bloklash",
        request=AdminUserBlockSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "is_blocked": {"type": "boolean"},
                },
            }
        },
    )
    @action(detail=True, methods=["post"], url_path="block")
    def block_user(self, request, pk=None):
        serializer = AdminUserBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.get_object()
        reason_key = serializer.validated_data["reason"]
        reason_labels = dict(AdminUserBlockSerializer.REASON_CHOICES)
        reason_display = reason_labels.get(reason_key, reason_key)

        from .services import block_user as block_user_service

        block_user_service(user, reason=reason_display)

        # notify_user=True bo'lsa FCM orqali xabar yuborish — Celery sozlangach aktivlashtirish kerak

        return Response(
            {
                "message": "Foydalanuvchi muvaffaqiyatli bloklandi.",
                "is_blocked": True,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(summary="Foydalanuvchini blokdan chiqarish")
    @action(detail=True, methods=["post"], url_path="unblock")
    def unblock_user(self, request, pk=None):
        user = self.get_object()
        user.is_blocked = False
        user.save(update_fields=["is_blocked"])

        from apps.core.utils.face import remove_user_faces_from_blocked

        remove_user_faces_from_blocked(user)

        return Response(
            {
                "message": "Foydalanuvchi blokdan chiqarildi.",
                "is_blocked": False,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Foydalanuvchiga kelib tushgan shikoyatlar",
        responses={200: AdminUserComplaintSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="complaints")
    def complaints(self, request, pk=None):
        from apps.accounts.complaints.models import Complaint

        user = self.get_object()
        qs = (
            Complaint.objects.filter(to_user=user)
            .select_related("from_user", "from_user__profile")
            .active()
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = AdminUserComplaintSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(AdminUserComplaintSerializer(qs, many=True).data)

    @extend_schema(
        summary="Foydalanuvchi moslik so'rovlari tarixi",
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                enum=["pending", "accepted", "rejected"],
                required=False,
                description="So'rov holati bo'yicha filtrlash",
            )
        ],
        responses={200: AdminUserMatchHistorySerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="match-history")
    def match_history(self, request, pk=None):
        from django.db.models import Q

        from apps.matches.match_requests.models import MatchRequest

        user = self.get_object()
        profile = getattr(user, "profile", None)
        if not profile:
            return Response([])

        qs = (
            MatchRequest.objects.filter(Q(from_profile=profile) | Q(to_profile=profile))
            .select_related("from_profile", "to_profile")
            .prefetch_related("from_profile__photos", "to_profile__photos")
            .active()
        )

        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        context = {**self.get_serializer_context(), "user_profile": profile}
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = AdminUserMatchHistorySerializer(
                page, many=True, context=context
            )
            return self.get_paginated_response(serializer.data)
        return Response(
            AdminUserMatchHistorySerializer(qs, many=True, context=context).data
        )

    @extend_schema(
        summary="Foydalanuvchi tarix voqealari",
        responses={200: AdminUserHistorySerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        user = self.get_object()
        events = build_user_history(user)
        serializer = AdminUserHistorySerializer(events, many=True)
        return Response(serializer.data)


class UserPledgeViewSet(BaseManageViewSet):
    queryset = UserPledge.objects.select_related("user").active()
    serializer_class = UserPledgeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserPledgeFilter
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        # user read-only bo'lgani uchun DRF ning takrorlanish validatori ishlamaydi,
        # shuning uchun bitta foydalanuvchiga bitta rozilik shartini shu yerda
        # tekshiramiz — aks holda baza cheklovi 500 xato beradi.
        if UserPledge.objects.filter(user=self.request.user).exists():
            raise ValidationError("Siz allaqachon halollik roziligini bergansiz.")

        serializer.save(user=self.request.user)


class UserDeviceViewSet(BaseManageViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserDeviceSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["last_active", "created_at"]
    http_method_names = ["get", "delete", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = UserDevice.objects.filter(is_active=True)
        if user.is_staff or user.is_superuser:
            return qs
        return qs.filter(user=user)

    def perform_destroy(self, instance):
        instance.delete()
        from .services import revoke_device_in_redis

        revoke_device_in_redis(instance.user_id, instance.device_id)

    @action(detail=False, methods=["post"], url_path="logout-all-others")
    def logout_all_others(self, request):
        user = request.user
        current_device_id = request.headers.get("X-Device-Id") or request.META.get(
            "HTTP_X_DEVICE_ID"
        )

        from .services import revoke_all_other_devices

        count = revoke_all_other_devices(user, current_device_id)

        return Response(
            {
                "message": f"Boshqa barcha qurilmalar ({count} ta) seansi muvaffaqiyatli tugatildi.",
                "terminated_count": count,
            },
            status=status.HTTP_200_OK,
        )


class GoogleLoginView(AutoSchemaMixin, views.APIView):
    permission_classes = []
    serializer_class = GoogleLoginSerializer

    @extend_schema(parameters=DEVICE_HEADER_PARAMETERS)
    def post(self, request, *args, **kwargs):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .services import authenticate_google_user

        user, tokens, is_blocked = authenticate_google_user(
            serializer.validated_data["id_token"], request
        )

        if is_blocked:
            return Response(
                {
                    "detail": "Sizning hisobingiz bloklangan. Iltimos, qo'llab-quvvatlash xizmatiga murojaat qiling."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class PhoneAuthView(AutoSchemaMixin, views.APIView):
    permission_classes = []
    serializer_class = PhoneAuthSerializer

    @extend_schema(parameters=DEVICE_HEADER_PARAMETERS)
    def post(self, request, *args, **kwargs):
        serializer = PhoneAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .services import authenticate_phone_user

        user, tokens, is_blocked = authenticate_phone_user(
            serializer.validated_data["phone_number"], request
        )

        if is_blocked:
            return Response(
                {
                    "detail": "Sizning hisobingiz bloklangan. Iltimos, qo'llab-quvvatlash xizmatiga murojaat qiling."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class EmailAuthView(AutoSchemaMixin, views.APIView):
    permission_classes = []
    serializer_class = EmailAuthSerializer

    @extend_schema(parameters=DEVICE_HEADER_PARAMETERS)
    def post(self, request, *args, **kwargs):
        serializer = EmailAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .services import authenticate_email_user

        user, tokens, is_blocked = authenticate_email_user(
            serializer.validated_data["email"], request
        )

        if is_blocked:
            return Response(
                {
                    "detail": "Sizning hisobingiz bloklangan. Iltimos, qo'llab-quvvatlash xizmatiga murojaat qiling."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class CustomTokenObtainPairView(AutoSchemaMixin, TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [CustomScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            for throttle in self.get_throttles():
                if hasattr(throttle, "get_cache_key") and hasattr(throttle, "cache"):
                    if hasattr(throttle, "scope_attr"):
                        throttle.scope = getattr(self, throttle.scope_attr, None)
                    cache_key = throttle.get_cache_key(request, view=self)
                    if cache_key:
                        throttle.cache.delete(cache_key)

        return response


class CustomTokenRefreshView(AutoSchemaMixin, TokenRefreshView):
    pass


class ChangePasswordView(AutoSchemaMixin, generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["put"]

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            offline_secret = hashlib.sha256(
                request.user.password.encode("utf-8")
            ).hexdigest()

            return Response(
                {
                    "message": "Parol muvaffaqiyatli o'zgartirildi.",
                    "offline_secret": offline_secret,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BlockedUserViewSet(BaseManageViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BlockedUserSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = BlockedUser.objects.select_related(
            "blocker", "blocked", "blocked__profile"
        ).active()

        return qs.filter(blocker=user)

    def perform_create(self, serializer):
        serializer.save(blocker=self.request.user)
