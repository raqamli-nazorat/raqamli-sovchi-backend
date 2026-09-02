from rest_framework.routers import DefaultRouter

from .views import (
    EducationLevelViewSet,
    HealthStatusViewSet,
    KinshipViewSet,
    MaritalStatusViewSet,
    NationalityViewSet,
    ProfessionViewSet,
)

router = DefaultRouter()
router.register("education-levels", EducationLevelViewSet, basename="education-levels")
router.register("nationalities", NationalityViewSet, basename="nationalities")
router.register("professions", ProfessionViewSet, basename="professions")
router.register("marital-statuses", MaritalStatusViewSet, basename="marital-statuses")
router.register("health-statuses", HealthStatusViewSet, basename="health-statuses")
router.register("kinships", KinshipViewSet, basename="kinships")

urlpatterns = router.urls
