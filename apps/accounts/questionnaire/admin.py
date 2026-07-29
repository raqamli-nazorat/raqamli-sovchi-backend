from django.contrib import admin
from apps.core.base.admin import BaseModelAdmin
from .models import Question, QuestionOption, UserAnswer


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 4


@admin.register(Question)
class QuestionAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "order",
        "section",
        "target_gender",
        "is_trap_question",
        "text",
        "created_at",
    )
    list_filter = ("section", "target_gender", "is_trap_question")
    search_fields = ("text",)
    ordering = ("target_gender", "order")
    inlines = [QuestionOptionInline]


@admin.register(QuestionOption)
class QuestionOptionAdmin(BaseModelAdmin):
    list_display = ("id", "question", "option_letter", "text", "weight")
    list_filter = ("option_letter", "question__target_gender", "question__section")
    search_fields = ("text", "question__text")


@admin.register(UserAnswer)
class UserAnswerAdmin(BaseModelAdmin):
    list_display = ("id", "profile", "question", "selected_option", "created_at")
    list_filter = ("question__section", "selected_option__option_letter")
    search_fields = ("profile__first_name", "profile__last_name", "question__text")
