from django.urls import path
from .views import VerifyCodeView

urlpatterns = [
    path("verify/", VerifyCodeView.as_view(), name="telegram-bot-verify"),
]
