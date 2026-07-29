from django.urls import path, include

urlpatterns = [
    path("locations/", include("apps.core.locations.urls")),
    path("audits/", include("apps.core.audits.urls")),
    path("dashboard/", include("apps.core.dashboard.urls")),
]
