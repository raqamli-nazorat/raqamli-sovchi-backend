import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

from apps.accounts.notifications.middleware import TicketAuthMiddleware
from apps.accounts.notifications.routing import (
    websocket_urlpatterns as notification_websocket_urlpatterns,
)
from apps.matches.chats.routing import (
    websocket_urlpatterns as chat_websocket_urlpatterns,
)

websocket_urlpatterns = notification_websocket_urlpatterns + chat_websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": TicketAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
