from django.urls import path, include

urlpatterns = [
    path("", include("apps.matches.match_requests.urls")),
    path("", include("apps.matches.chats.urls")),
]
