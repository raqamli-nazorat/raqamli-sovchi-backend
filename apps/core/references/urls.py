from rest_framework.routers import DefaultRouter
from .views import (
    EducationLevelViewSet,
    NationalityViewSet,
    ProfessionViewSet,
    MaritalStatusViewSet,
    HealthStatusViewSet,
)

router = DefaultRouter()
router.register("education-levels", EducationLevelViewSet, basename="education-levels")
router.register("nationalities", NationalityViewSet, basename="nationalities")
router.register("professions", ProfessionViewSet, basename="professions")
router.register("marital-statuses", MaritalStatusViewSet, basename="marital-statuses")
router.register("health-statuses", HealthStatusViewSet, basename="health-statuses")

urlpatterns = router.urls
