from django.urls import path

from .views import (
    WebSocketTicketView,
    NotificationListView,
    NotificationCountView,
    MarkNotificationReadView,
    MarkAllNotificationsAsReadView,
    UserDeviceRegisterView,
    UserDeviceUnregisterView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications"),
    path("count/", NotificationCountView.as_view(), name="notifications-count"),
    path(
        "<uuid:pk>/read/", MarkNotificationReadView.as_view(), name="read-notifications"
    ),
    path(
        "read-all/",
        MarkAllNotificationsAsReadView.as_view(),
        name="read-all-notifications",
    ),
    path("tickets/", WebSocketTicketView.as_view(), name="websocket_tickets"),
    path("devices/register/", UserDeviceRegisterView.as_view(), name="device-register"),
    path(
        "devices/current/", UserDeviceUnregisterView.as_view(), name="device-unregister"
    ),
]
