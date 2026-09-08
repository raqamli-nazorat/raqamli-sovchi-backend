from django.urls import include, path

urlpatterns = [
    path("locations/", include("apps.core.locations.urls")),
    path("references/", include("apps.core.references.urls")),
    path("audits/", include("apps.core.audits.urls")),
    path("dashboard/", include("apps.core.dashboard.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("matches/", include("apps.matches.urls")),
    path("psychologists/", include("apps.consulting.urls")),
]
