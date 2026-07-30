from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.base.views import BaseManageViewSet
from apps.core.base.mixins import AutoSchemaMixin
from .models import User, UserPledge, AuthProvider
from .serializers import (
    UserSerializer,
    UserPledgeSerializer,
    GoogleLoginSerializer,
    PhoneAuthSerializer, CustomTokenObtainPairSerializer,
)
from .filters import UserFilter, UserPledgeFilter
from ...core.utils.throttles import CustomScopedRateThrottle


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class UserViewSet(BaseManageViewSet):
    queryset = User.objects.active()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ["phone_number", "email"]
    ordering_fields = ["created_at", "phone_number"]


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
