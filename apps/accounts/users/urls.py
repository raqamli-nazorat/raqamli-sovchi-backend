from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    GoogleLoginView,
    PermissionViewSet,
    PhoneAuthView,
    RoleViewSet,
    UserMeView,
    UserPledgeViewSet,
    UserViewSet, ChangePasswordView,
)

router = DefaultRouter()
router.register(r"permissions", PermissionViewSet, basename="permission")
router.register(r"roles", RoleViewSet, basename="role")
router.register(r"users", UserViewSet, basename="user")
router.register(r"pledges", UserPledgeViewSet, basename="user-pledge")

urlpatterns = [
    path("users/me/", UserMeView.as_view(), name="user-me"),
    path("auth/google/", GoogleLoginView.as_view(), name="auth-google"),
    path("auth/phone/", PhoneAuthView.as_view(), name="auth-phone"),
    path("auth/token/", CustomTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path(
        "auth/token/refresh/",
        CustomTokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path("", include(router.urls)),
]
