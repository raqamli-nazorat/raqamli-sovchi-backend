from rest_framework import serializers

from apps.core.base.serializers import BaseModelSerializer

from .models import Question, QuestionOption, SectionType, UserAnswer


class SectionTypeSerializer(BaseModelSerializer):
    count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SectionType
        fields = "__all__"

    def get_count(self, obj):
        return obj.questions.count()


class QuestionOptionSerializer(BaseModelSerializer):
    class Meta:
        model = QuestionOption
        fields = "__all__"


class QuestionOptionBulkItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, allow_null=True)
    question = serializers.UUIDField(required=False, allow_null=True)
    question_id = serializers.UUIDField(required=False, allow_null=True)
    option_letter = serializers.ChoiceField(
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")], required=True
    )
    text = serializers.CharField(required=True)
    weight = serializers.IntegerField(default=0, min_value=0, max_value=10)


class QuestionOptionBulkSerializer(serializers.Serializer):
    question_id = serializers.UUIDField(required=True)
    options = QuestionOptionBulkItemSerializer(many=True, required=True)


class QuestionSerializer(BaseModelSerializer):
    class Meta:
        model = Question
        fields = "__all__"
        related_fields = {
            "section": ["id", "name"],
            "options": ["id", "option_letter", "text", "weight"],
        }


class CurrentProfileDefault:
    """
    So'rov yuborayotgan foydalanuvchining anketasini standart qiymat sifatida beradi.

    UserAnswer da (profile, question) juftligi unique. DRF ning
    UniqueTogetherValidator-i tekshiruv uchun ikkala maydonning ham qiymatini
    talab qiladi, shuning uchun profile ni shu yerda avtomatik to'ldiramiz —
    aks holda mijoz uni qo'lda yuborishga majbur bo'lardi.
    """

    requires_context = True

    def __call__(self, serializer_field):
        request = serializer_field.context.get("request")
        return getattr(getattr(request, "user", None), "profile", None)


class UserAnswerSerializer(BaseModelSerializer):
    class Meta:
        model = UserAnswer
        fields = "__all__"
        # profile so'rov yuboruvchidan avtomatik olinadi. Oddiy foydalanuvchi
        # yuborgan qiymat view ichida (perform_create) baribir almashtiriladi —
        # faqat xodim boshqa profil uchun javob kirita oladi.
        extra_kwargs = {
            "profile": {"required": False, "default": CurrentProfileDefault()}
        }
        related_fields = {
            "profile": ["id", "first_name", "last_name"],
            "question": ["id", "order", "text", "section"],
            "selected_option": ["id", "option_letter", "text", "weight"],
        }


class BulkAnswerItemSerializer(serializers.Serializer):
    question_id = serializers.UUIDField(required=True)
    selected_option_id = serializers.UUIDField(required=True)


class BulkUserAnswerSerializer(serializers.Serializer):
    profile_id = serializers.UUIDField(required=True)
    answers = BulkAnswerItemSerializer(many=True, required=True)
