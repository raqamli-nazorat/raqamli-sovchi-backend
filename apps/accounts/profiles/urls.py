from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProfileViewSet,
    ProfilePhotoViewSet,
    RepresentativeInfoViewSet,
)

router = DefaultRouter()
router.register(r"profiles", ProfileViewSet, basename="profile")
router.register(r"photos", ProfilePhotoViewSet, basename="profile-photo")
router.register(r"representatives", RepresentativeInfoViewSet, basename="representative-info")

urlpatterns = [
    path("", include(router.urls)),
]
