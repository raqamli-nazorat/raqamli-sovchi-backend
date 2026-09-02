from rest_framework.routers import DefaultRouter

from .views import PhotoRequestViewSet

router = DefaultRouter()
router.register(r"photo-requests", PhotoRequestViewSet, basename="photo-request")

urlpatterns = router.urls
