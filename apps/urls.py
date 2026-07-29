from django.urls import path, include

urlpatterns = [
    path("locations/", include("apps.core.locations.urls")),
    path("accounts/", include("apps.accounts.urls")),
]
