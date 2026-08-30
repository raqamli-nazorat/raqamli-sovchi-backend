from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.profiles.models import GenderType, Profile
from apps.accounts.questionnaire.models import (
    Question,
    QuestionOption,
    SectionType,
    UserAnswer,
)
from apps.accounts.users.models import AuthProvider, Role, User


class QuestionnaireTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        # post_migrate signali yaratgan haqiqiy boshlang'ich rol ishlatiladi —
        # unda oddiy foydalanuvchining real huquqlari bor. Yangi bo'sh rol
        # yaratilsa, u haqiqiysini almashtirib yuboradi va hamma so'rov 403 bo'ladi.
        self.role = Role.objects.filter(is_default=True).first()
        self.user = User.objects.create(
            phone_number="+998901234567",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile = Profile.objects.create(
            user=self.user,
            first_name="Test",
            last_name="User",
            gender=GenderType.MALE,
            birth_year=1995,
            height=175,
        )

        self.section = SectionType.objects.create(name="Dunyoqarash va Qadriyatlar")
        self.question = Question.objects.create(
            section=self.section,
            text="Hayotdagi eng muhim qadriyatingiz nima?",
            target_gender="all",
            order=1,
        )
        self.option_a = QuestionOption.objects.create(
            question=self.question,
            option_letter="A",
            text="Oila va halollik",
            weight=10,
        )
        self.option_b = QuestionOption.objects.create(
            question=self.question,
            option_letter="B",
            text="Karyera",
            weight=5,
        )

    def test_get_sections_list(self):
        self.client.force_authenticate(user=self.user)
        url = "/api/v1/accounts/section-types/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_questions_list(self):
        self.client.force_authenticate(user=self.user)
        url = "/api/v1/accounts/questions/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_submit_answer(self):
        self.client.force_authenticate(user=self.user)
        url = "/api/v1/accounts/answers/"
        data = {
            "question": str(self.question.id),
            "selected_option": str(self.option_a.id),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        answer_exists = UserAnswer.objects.filter(
            profile=self.profile,
            question=self.question,
            selected_option=self.option_a,
        ).exists()
        self.assertTrue(answer_exists)
