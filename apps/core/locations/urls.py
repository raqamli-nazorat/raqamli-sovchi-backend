from rest_framework.routers import SimpleRouter
from .views import (
    RegionViewSet,
    DistrictViewSet,
)

router = SimpleRouter()
router.register(r"region", RegionViewSet)
router.register(r"district", DistrictViewSet)

urlpatterns = router.urls
