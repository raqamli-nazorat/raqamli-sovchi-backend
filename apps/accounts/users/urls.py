from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    UserPledgeViewSet,
    GoogleLoginView,
    PhoneAuthView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"pledges", UserPledgeViewSet, basename="user-pledge")

urlpatterns = [
    path("auth/google/", GoogleLoginView.as_view(), name="auth-google"),
    path("auth/phone/", PhoneAuthView.as_view(), name="auth-phone"),
    path("auth/token/", CustomTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/token/refresh/", CustomTokenRefreshView.as_view(), name="token-refresh"),
    path("", include(router.urls)),
]

