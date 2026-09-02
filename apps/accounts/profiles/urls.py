from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FaceVerificationView,
    ProfileMeView,
    ProfilePhotoViewSet,
    ProfileViewSet,
    RepresentativeInfoViewSet,
    SavedProfileViewSet,
)

router = DefaultRouter()
router.register(r"profiles", ProfileViewSet, basename="profile")
router.register(r"photos", ProfilePhotoViewSet, basename="profile-photo")
router.register(
    r"representatives", RepresentativeInfoViewSet, basename="representative-info"
)
router.register(r"saved-profiles", SavedProfileViewSet, basename="saved-profile")

urlpatterns = [
    path("profiles/me/", ProfileMeView.as_view(), name="profile-me"),
    path("face-verify/", FaceVerificationView.as_view(), name="face-verify"),
    path("", include(router.urls)),
]
