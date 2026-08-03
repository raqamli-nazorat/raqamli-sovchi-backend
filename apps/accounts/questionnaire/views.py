from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from django.db import transaction

from apps.core.base.views import BaseManageViewSet
from apps.core.base.mixins import AutoSchemaMixin
from .models import SectionType, Question, QuestionOption, UserAnswer
from .serializers import (
    SectionTypeSerializer,
    QuestionSerializer,
    QuestionOptionSerializer,
    QuestionOptionBulkSerializer,
    UserAnswerSerializer,
    BulkUserAnswerSerializer,
)
from .filters import QuestionFilter, UserAnswerFilter


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
        """
        Bulk create and bulk update question options in a single request.
        Supports both direct Array [] payload and Dictionary {} payload.
        """
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

        existing_options = {
            opt.option_letter: opt
            for opt in QuestionOption.objects.filter(question_id=question_id)
        }

        existing_by_id = {str(opt.id): opt for opt in existing_options.values()}

        to_create = []
        to_update = []

        with transaction.atomic():
            for item in options_data:
                item_id = str(item.get("id")) if item.get("id") else None
                letter = item["option_letter"]
                text = item["text"]
                weight = item["weight"]

                target_opt = None
                if item_id and item_id in existing_by_id:
                    target_opt = existing_by_id[item_id]
                elif letter in existing_options:
                    target_opt = existing_options[letter]

                if target_opt:
                    target_opt.option_letter = letter
                    target_opt.text = text
                    target_opt.weight = weight
                    to_update.append(target_opt)
                else:
                    new_opt = QuestionOption(
                        question_id=question_id,
                        option_letter=letter,
                        text=text,
                        weight=weight,
                    )
                    to_create.append(new_opt)

            created_count = 0
            updated_count = 0

            if to_create:
                QuestionOption.objects.bulk_create(to_create)
                created_count = len(to_create)

            if to_update:
                QuestionOption.objects.bulk_update(
                    to_update, fields=["option_letter", "text", "weight"]
                )
                updated_count = len(to_update)

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
