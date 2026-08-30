from rest_framework.routers import DefaultRouter

from .views import ChatRoomViewSet, MessageViewSet

router = DefaultRouter()
router.register(r"chat-rooms", ChatRoomViewSet, basename="chat-room")
router.register(r"messages", MessageViewSet, basename="message")

urlpatterns = router.urls
