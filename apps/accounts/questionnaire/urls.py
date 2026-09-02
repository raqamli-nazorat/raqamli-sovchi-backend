from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BulkUserAnswerSubmitView,
    QuestionOptionViewSet,
    QuestionViewSet,
    SectionTypeViewSet,
    UserAnswerViewSet,
)

router = DefaultRouter()
router.register(r"section-types", SectionTypeViewSet, basename="section-type")
router.register(r"questions", QuestionViewSet, basename="question")
router.register(r"options", QuestionOptionViewSet, basename="question-option")
router.register(r"answers", UserAnswerViewSet, basename="user-answer")

urlpatterns = [
    path(
        "answers/bulk-submit/",
        BulkUserAnswerSubmitView.as_view(),
        name="bulk-answer-submit",
    ),
    path("", include(router.urls)),
]
