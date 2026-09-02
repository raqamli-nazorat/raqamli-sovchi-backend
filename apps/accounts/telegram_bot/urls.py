from django.urls import path

from .views import (
    CheckAuthSessionStatusView,
    CreateAuthSessionView,
)

urlpatterns = [
    path(
        "auth-session/create/",
        CreateAuthSessionView.as_view(),
        name="telegram-session-create",
    ),
    path(
        "auth-session/<uuid:session_id>/status/",
        CheckAuthSessionStatusView.as_view(),
        name="telegram-session-status",
    ),
]
