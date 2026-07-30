from django.urls import path, include

urlpatterns = [
    path("", include("apps.accounts.users.urls")),
    path("", include("apps.accounts.profiles.urls")),
    path("", include("apps.accounts.questionnaire.urls")),
    path("telegram-bot/", include("apps.accounts.telegram_bot.urls")),
]
