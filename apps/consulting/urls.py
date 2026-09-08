from django.urls import include, path

urlpatterns = [
    path("", include("apps.consulting.psychologists.urls")),
]
