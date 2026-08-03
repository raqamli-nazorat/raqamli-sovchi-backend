from django.urls import path, include

urlpatterns = [
    path("locations/", include("apps.core.locations.urls")),
    path("references/", include("apps.core.references.urls")),
    path("audits/", include("apps.core.audits.urls")),
]
