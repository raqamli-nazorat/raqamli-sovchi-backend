import hashlib

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from django.contrib.auth.models import Permission
from django.db.models import Count, IntegerField, OuterRef, Subquery
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status, views
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.base.mixins import AutoSchemaMixin
from apps.core.base.views import BaseManageViewSet, BaseReadOnlyViewSet
from apps.core.utils.throttles import CustomScopedRateThrottle

from .filters import RoleFilter, UserFilter, UserPledgeFilter
from .models import AuthProvider, Role, User, UserPledge
from .serializers import (
    CustomTokenObtainPairSerializer,
    GoogleLoginSerializer,
    PermissionSerializer,
    PhoneAuthSerializer,
    RoleSerializer,
    UserListSerializer,
    UserPledgeSerializer,
    UserSerializer,
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

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer
        return super().get_serializer_class()


class UserPledgeViewSet(BaseManageViewSet):
    queryset = UserPledge.objects.select_related("user").active()
    serializer_class = UserPledgeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserPledgeFilter
    ordering_fields = ["created_at"]


class GoogleLoginView(AutoSchemaMixin, views.APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access_token = serializer.validated_data["access_token"]
        phone_number = serializer.validated_data["phone_number"]

        adapter = GoogleOAuth2Adapter(request)
        try:
            token = adapter.parse_token({"access_token": access_token})
            social_login = adapter.complete_login(
                request,
                adapter.get_provider().app,
                token,
                response={"access_token": access_token},
            )
        except OAuth2Error as exc:
            raise ValidationError(str(exc))

        email = social_login.account.extra_data.get("email", "")
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                "email": email or None,
                "auth_provider": AuthProvider.GOOGLE,
            },
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

        social_login.user = user
        social_login.lookup()
        social_login.save(request, connect=True)

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

        if not created and user.auth_provider != AuthProvider.PHONE:
            user.auth_provider = AuthProvider.PHONE
            user.save(update_fields=["auth_provider"])

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
