from django.urls import include, path

urlpatterns = [
    path("", include("apps.matches.match_requests.urls")),
    path("", include("apps.matches.chats.urls")),
    path("", include("apps.matches.photo_requests.urls")),
]
