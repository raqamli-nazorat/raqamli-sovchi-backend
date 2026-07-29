from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    UserPledgeViewSet,
    GoogleLoginView,
    PhoneAuthView,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"pledges", UserPledgeViewSet, basename="user-pledge")

urlpatterns = [
    path("auth/google/", GoogleLoginView.as_view(), name="auth-google"),
    path("auth/phone/", PhoneAuthView.as_view(), name="auth-phone"),
    path("", include(router.urls)),
]
