from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    QuestionViewSet,
    QuestionOptionViewSet,
    UserAnswerViewSet,
    BulkUserAnswerSubmitView,
)

router = DefaultRouter()
router.register(r"questions", QuestionViewSet, basename="question")
router.register(r"options", QuestionOptionViewSet, basename="question-option")
router.register(r"answers", UserAnswerViewSet, basename="user-answer")

urlpatterns = [
    path("answers/bulk-submit/", BulkUserAnswerSubmitView.as_view(), name="bulk-answer-submit"),
    path("", include(router.urls)),
]
