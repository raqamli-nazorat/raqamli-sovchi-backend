from django.urls import path, include

urlpatterns = [
    path("users/", include("apps.accounts.users.urls")),
    path("profiles/", include("apps.accounts.profiles.urls")),
    path("questionnaire/", include("apps.accounts.questionnaire.urls")),
    path("telegram-bot/", include("apps.accounts.telegram_bot.urls")),
]
