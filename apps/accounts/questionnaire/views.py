from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.base.views import BaseManageViewSet, BaseReadOnlyViewSet
from apps.core.base.mixins import AutoSchemaMixin
from .models import Question, QuestionOption, UserAnswer
from .serializers import (
    QuestionSerializer,
    QuestionOptionSerializer,
    UserAnswerSerializer,
    BulkUserAnswerSerializer,
)
from .filters import QuestionFilter, UserAnswerFilter

class QuestionViewSet(BaseReadOnlyViewSet):
    queryset = Question.objects.prefetch_related("options").active()
    serializer_class = QuestionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = QuestionFilter
    search_fields = ["text"]
    ordering_fields = ["order", "created_at"]

class QuestionOptionViewSet(BaseReadOnlyViewSet):
    queryset = QuestionOption.objects.select_related("question").active()
    serializer_class = QuestionOptionSerializer

class UserAnswerViewSet(BaseManageViewSet):
    queryset = UserAnswer.objects.select_related(
        "profile", "question", "selected_option"
    ).active()
    serializer_class = UserAnswerSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserAnswerFilter

class BulkUserAnswerSubmitView(AutoSchemaMixin, views.APIView):
    def post(self, request, *args, **kwargs):
        serializer = BulkUserAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile_id = serializer.validated_data["profile_id"]
        answers_data = serializer.validated_data["answers"]

        created_answers = []
        for item in answers_data:
            ans, _ = UserAnswer.objects.update_or_create(
                profile_id=profile_id,
                question_id=item["question_id"],
                defaults={"selected_option_id": item["selected_option_id"]},
            )
            created_answers.append(ans)

        return Response(
            {
                "message": "Javoblar muvaffaqiyatli saqlandi.",
                "total_submitted": len(created_answers),
            },
            status=status.HTTP_200_OK,
        )
