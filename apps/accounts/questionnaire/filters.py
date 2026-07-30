import django_filters
from apps.core.base.filters import UUIDInFilter
from .models import Question, UserAnswer

class QuestionFilter(django_filters.FilterSet):
    section = django_filters.CharFilter(field_name="section", lookup_expr="exact")
    target_gender = django_filters.CharFilter(
        field_name="target_gender", lookup_expr="exact"
    )
    is_trap_question = django_filters.BooleanFilter(field_name="is_trap_question")

    class Meta:
        model = Question
        fields = ["section", "target_gender", "is_trap_question"]

class UserAnswerFilter(django_filters.FilterSet):
    profile = UUIDInFilter(field_name="profile", lookup_expr="in")
    question = UUIDInFilter(field_name="question", lookup_expr="in")

    class Meta:
        model = UserAnswer
        fields = ["profile", "question"]
