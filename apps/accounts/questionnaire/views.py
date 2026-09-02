from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, views
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.core.base.mixins import AutoSchemaMixin
from apps.core.base.views import BaseManageViewSet

from .filters import QuestionFilter, UserAnswerFilter
from .models import Question, QuestionOption, SectionType, UserAnswer
from .permissions import IsUserAnswerOwnerOrStaff
from .serializers import (
    BulkUserAnswerSerializer,
    QuestionOptionBulkItemSerializer,
    QuestionOptionBulkSerializer,
    QuestionOptionSerializer,
    QuestionSerializer,
    SectionTypeSerializer,
    UserAnswerSerializer,
)


class SectionTypeViewSet(BaseManageViewSet):
    queryset = SectionType.objects.prefetch_related("questions").active()
    serializer_class = SectionTypeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]


class QuestionViewSet(BaseManageViewSet):
    queryset = (
        Question.objects.select_related("section").prefetch_related("options").active()
    )
    serializer_class = QuestionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = QuestionFilter
    search_fields = ["text"]
    ordering_fields = ["order", "created_at"]


class QuestionOptionViewSet(BaseManageViewSet):
    queryset = QuestionOption.objects.select_related("question").active()
    serializer_class = QuestionOptionSerializer

    @action(detail=False, methods=["post", "put", "patch"], url_path="bulk")
    def bulk_options(self, request, *args, **kwargs):
        if isinstance(request.data, list):
            serializer = QuestionOptionBulkItemSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            options_data = serializer.validated_data
            if not options_data:
                return Response(
                    {"detail": "Kamida 1 ta variant yuborilishi kerak."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            question_id = options_data[0].get("question") or options_data[0].get(
                "question_id"
            )
            if not question_id:
                return Response(
                    {"detail": "question yoki question_id ko'rsatilishi shart."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            serializer = QuestionOptionBulkSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            question_id = serializer.validated_data["question_id"]
            options_data = serializer.validated_data["options"]

        from .services import bulk_save_question_options

        created_count, updated_count = bulk_save_question_options(
            question_id, options_data
        )

        result_options = QuestionOption.objects.filter(
            question_id=question_id
        ).order_by("option_letter")
        result_serializer = QuestionOptionSerializer(result_options, many=True)

        return Response(
            {
                "message": f"Variantlar muvaffaqiyatli saqlandi ({created_count} ta yaratildi, {updated_count} ta yangilandi).",
                "created_count": created_count,
                "updated_count": updated_count,
                "options": result_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class UserAnswerViewSet(BaseManageViewSet):
    serializer_class = UserAnswerSerializer
    permission_classes = [IsUserAnswerOwnerOrStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserAnswerFilter

    def get_queryset(self):
        qs = UserAnswer.objects.select_related(
            "profile", "question", "selected_option"
        ).active()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()

        if (
            user.is_staff
            or user.is_superuser
            or bool(getattr(user, "role", None) and not user.role.is_default)
        ):
            return qs

        user_profile = getattr(user, "profile", None)
        if not user_profile:
            return qs.none()

        return qs.filter(profile=user_profile)

    def perform_create(self, serializer):
        user = self.request.user
        if not (user.is_staff or user.is_superuser):
            user_profile = getattr(user, "profile", None)
            if not user_profile:
                from rest_framework.exceptions import ValidationError

                raise ValidationError({"detail": "Foydalanuvchi profili topilmadi."})
            serializer.save(profile=user_profile)
        else:
            serializer.save()


class BulkUserAnswerSubmitView(AutoSchemaMixin, views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BulkUserAnswerSerializer

    def post(self, request, *args, **kwargs):
        serializer = BulkUserAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile_id = serializer.validated_data["profile_id"]
        answers_data = serializer.validated_data["answers"]

        user = request.user
        if not (user.is_staff or user.is_superuser):
            user_profile = getattr(user, "profile", None)
            if not user_profile or str(user_profile.id) != str(profile_id):
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied(
                    "Faqat o'zingizning profilingiz uchun javoblarni saqlashingiz mumkin."
                )

        from .services import bulk_save_user_answers

        total_submitted = bulk_save_user_answers(profile_id, answers_data)

        return Response(
            {
                "message": "Javoblar muvaffaqiyatli saqlandi.",
                "total_submitted": total_submitted,
            },
            status=status.HTTP_200_OK,
        )
