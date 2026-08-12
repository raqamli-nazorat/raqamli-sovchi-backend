from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    GoogleLoginView,
    PermissionViewSet,
    PhoneAuthView,
    EmailAuthView,
    RoleViewSet,
    UserMeView,
    UserPledgeViewSet,
    UserViewSet,
    UserDeviceViewSet,
    ChangePasswordView,
    BlockedUserViewSet,
)

router = DefaultRouter()
router.register(r"permissions", PermissionViewSet, basename="permission")
router.register(r"roles", RoleViewSet, basename="role")
router.register(r"users", UserViewSet, basename="user")
router.register(r"pledges", UserPledgeViewSet, basename="user-pledge")
router.register(r"devices", UserDeviceViewSet, basename="user-device")
router.register(r"blocked-users", BlockedUserViewSet, basename="blocked-user")

urlpatterns = [
    path("users/me/", UserMeView.as_view(), name="user-me"),
    path("auth/google/", GoogleLoginView.as_view(), name="auth-google"),
    path("auth/phone/", PhoneAuthView.as_view(), name="auth-phone"),
    path("auth/email/", EmailAuthView.as_view(), name="auth-email"),
    path("auth/token/", CustomTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path(
        "auth/token/refresh/",
        CustomTokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path("", include(router.urls)),
]
