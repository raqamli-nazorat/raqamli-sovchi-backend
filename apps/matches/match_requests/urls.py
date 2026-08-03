from rest_framework.routers import DefaultRouter
from .views import MatchRequestViewSet

router = DefaultRouter()
router.register(r"match-requests", MatchRequestViewSet, basename="match-request")

urlpatterns = router.urls
