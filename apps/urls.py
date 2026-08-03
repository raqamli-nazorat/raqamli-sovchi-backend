from django.urls import path, include

urlpatterns = [
    path("locations/", include("apps.core.locations.urls")),
    path("references/", include("apps.core.references.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("matches/", include("apps.matches.urls")),
]
