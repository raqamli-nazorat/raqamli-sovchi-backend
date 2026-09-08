from rest_framework.routers import SimpleRouter

from .views import PsychologistViewSet

router = SimpleRouter()
router.register("", PsychologistViewSet, basename="psychologist")

urlpatterns = router.urls
