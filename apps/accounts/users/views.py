import hashlib
import requests as http_requests

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import Permission
from django.db.models import Count, IntegerField, OuterRef, Subquery
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status, views
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.base.mixins import AutoSchemaMixin
from apps.core.base.views import BaseManageViewSet, BaseReadOnlyViewSet
from apps.core.utils.throttles import CustomScopedRateThrottle

from .filters import RoleFilter, UserFilter, UserPledgeFilter
from .models import AuthProvider, Role, User, UserPledge, UserDevice
from .serializers import (
    CustomTokenObtainPairSerializer,
    GoogleLoginSerializer,
    PermissionSerializer,
    PhoneAuthSerializer,
    EmailAuthSerializer,
    RoleSerializer,
    UserPledgeSerializer,
    UserSerializer,
    UserDeviceSerializer,
    ChangePasswordSerializer,
)
from .utils import get_tokens_for_user


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
                grouped_data[group_key] = []

            grouped_data[group_key].append(
                {"id": perm["id"], "name": perm["name"], "codename": perm["codename"]}
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

    @action(detail=True, methods=["post"], url_path="block")
    def block_user(self, request, pk=None):
        user = self.get_object()
        user.is_blocked = True
        user.save(update_fields=["is_blocked"])

        from apps.core.utils.face import register_user_faces_as_blocked

        register_user_faces_as_blocked(user, reason="Admin tomonidan bloklandi")

        return Response(
            {
                "message": "Foydalanuvchi va uning yuzi muvaffaqiyatli bloklandi.",
                "is_blocked": True,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="unblock")
    def unblock_user(self, request, pk=None):
        user = self.get_object()
        user.is_blocked = False
        user.save(update_fields=["is_blocked"])

        from apps.core.utils.face import remove_user_faces_from_blocked

        remove_user_faces_from_blocked(user)

        return Response(
            {
                "message": "Foydalanuvchi va uning yuzi blokdan chiqarildi.",
                "is_blocked": False,
            },
            status=status.HTTP_200_OK,
        )


class UserPledgeViewSet(BaseManageViewSet):
    queryset = UserPledge.objects.select_related("user").active()
    serializer_class = UserPledgeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserPledgeFilter
    ordering_fields = ["created_at"]


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

    @action(detail=False, methods=["post"], url_path="logout-all-others")
    def logout_all_others(self, request):
        user = request.user
        current_device_id = request.headers.get("X-Device-Id") or request.META.get("HTTP_X_DEVICE_ID")

        qs = UserDevice.objects.filter(user=user, is_active=True)
        if current_device_id:
            qs = qs.exclude(device_id=current_device_id)

        count = qs.update(is_active=False)

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

    def post(self, request, *args, **kwargs):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        id_token_str = serializer.validated_data["id_token"]

        resp = http_requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token_str},
            timeout=10,
        )
        if resp.status_code != 200 or "error" in resp.json():
            raise ValidationError("Google ID token yaroqsiz yoki muddati o'tgan.")

        user_info = resp.json()
        google_uid = user_info.get("sub")
        email = (user_info.get("email") or "").lower().strip()

        if not google_uid:
            raise ValidationError("Google foydalanuvchi ma'lumotlarini olishda xatolik.")

        social_acc = SocialAccount.objects.filter(
            provider="google", uid=google_uid
        ).first()

        if social_acc:
            user = social_acc.user
            created = False
        else:
            user = None
            if email:
                user = User.objects.filter(email=email).first()
            if user:
                created = False
            else:
                user = User.objects.create(
                    email=email or None,
                    auth_provider=AuthProvider.GOOGLE,
                    is_verified=True,
                )
                created = True

        if not created and user.is_blocked:
            return Response(
                {
                    "detail": "Sizning hisobingiz bloklangan. Iltimos, qo'llab-quvvatlash xizmatiga murojaat qiling."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        update_fields = []
        if not user.email and email:
            user.email = email
            update_fields.append("email")
        if not created and user.auth_provider != AuthProvider.GOOGLE:
            user.auth_provider = AuthProvider.GOOGLE
            update_fields.append("auth_provider")
        if update_fields:
            user.save(update_fields=update_fields)

        if not social_acc:
            SocialAccount.objects.get_or_create(
                provider="google",
                uid=google_uid,
                defaults={"user": user, "extra_data": user_info},
            )

        from .services import register_or_update_user_device
        register_or_update_user_device(user, request)

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": tokens,
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PhoneAuthView(AutoSchemaMixin, views.APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = PhoneAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={"auth_provider": AuthProvider.PHONE},
        )

        if not created and user.is_blocked:
            return Response(
                {
                    "detail": "Sizning hisobingiz bloklangan. Iltimos, qo'llab-quvvatlash xizmatiga murojaat qiling."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not created and user.auth_provider != AuthProvider.PHONE:
            user.auth_provider = AuthProvider.PHONE
            user.save(update_fields=["auth_provider"])

        from .services import register_or_update_user_device
        register_or_update_user_device(user, request)

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": tokens,
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class EmailAuthView(AutoSchemaMixin, views.APIView):
    permission_classes = []
    serializer_class = EmailAuthSerializer

    def post(self, request, *args, **kwargs):
        serializer = EmailAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"auth_provider": AuthProvider.EMAIL},
        )

        if not created and user.is_blocked:
            return Response(
                {
                    "detail": "Sizning hisobingiz bloklangan. Iltimos, qo'llab-quvvatlash xizmatiga murojaat qiling."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not created and user.auth_provider != AuthProvider.EMAIL:
            user.auth_provider = AuthProvider.EMAIL
            user.save(update_fields=["auth_provider"])

        from .services import register_or_update_user_device
        register_or_update_user_device(user, request)

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": tokens,
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
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
