from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.complaints.models import Complaint, ComplaintStatus
from apps.accounts.complaints.services import (
    build_ai_analysis,
    get_questionnaire_progress,
)
from apps.accounts.notifications.models import Notification
from apps.accounts.profiles.models import CandidateRole, GenderType, Profile
from apps.accounts.questionnaire.models import (
    Question,
    QuestionOption,
    SectionType,
    TargetGender,
    UserAnswer,
)
from apps.accounts.users.models import AuthProvider, Role, User


class ComplaintApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.filter(is_default=True).first()
        self.url = "/api/v1/accounts/complaints/"

        self.user1, self.profile1 = self._make_user(
            "+998901100001",
            GenderType.FEMALE,
            CandidateRole.BRIDE,
            "Mohira",
            "Rasulova",
        )
        self.user2, self.profile2 = self._make_user(
            "+998901100002",
            GenderType.MALE,
            CandidateRole.GROOM,
            "Bekzod",
            "Qodirov",
        )
        self.user3, self.profile3 = self._make_user(
            "+998901100003",
            GenderType.MALE,
            CandidateRole.GROOM,
            "Jasur",
            "Toshmatov",
        )
        self.admin = User.objects.create(
            phone_number="+998901100010",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
            is_staff=True,
            is_superuser=True,
        )

    def _make_user(self, phone, gender, candidate_type, first_name, last_name):
        """Test uchun foydalanuvchi va profil yaratadi."""
        user = User.objects.create(
            phone_number=phone,
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        profile = Profile.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            candidate_type=candidate_type,
            birth_date="1995-01-01",
            height=175,
        )
        return user, profile

    def test_create_complaint_success(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            self.url,
            {
                "to_user": str(self.user2.id),
                "reason": "abusive_language",
                "message": "Suhbatda odobsiz so'z ishlatdi.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Complaint.objects.filter(from_user=self.user1, to_user=self.user2).exists()
        )

    def test_create_complaint_invalid_data(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            self.url,
            {
                "to_user": str(self.user1.id),
                "reason": "abusive_language",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_complaint_unauthenticated(self):
        response = self.client.post(
            self.url,
            {
                "to_user": str(self.user2.id),
                "reason": "abusive_language",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_complaints_success(self):
        Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="abusive_language",
        )
        Complaint.objects.create(
            from_user=self.user2,
            to_user=self.user3,
            reason="spam",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_list_complaints_forbidden(self):
        Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="abusive_language",
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_complaint_success(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
            message="Firibgarlik bo'yicha shikoyat.",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f"{self.url}{complaint.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], complaint.id)
        self.assertEqual(response.data["status"], ComplaintStatus.PENDING)

    def test_retrieve_complaint_forbidden(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"{self.url}{complaint.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_complaints_success(self):
        Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="abusive_language",
        )
        Complaint.objects.create(
            from_user=self.user2,
            to_user=self.user1,
            reason="spam",
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"{self.url}my/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_my_complaints_unauthenticated(self):
        response = self.client.get(f"{self.url}my/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_complaint_success(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
            message="Eski izoh.",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.put(
            f"{self.url}{complaint.id}/",
            {
                "to_user": str(self.user3.id),
                "reason": "spam",
                "message": "Yangilangan izoh.",
                "evidence": {"source": "manual"},
                "admin_note": "Admin tomonidan yangilandi.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        complaint.refresh_from_db()
        self.assertEqual(complaint.to_user, self.user3)
        self.assertEqual(complaint.reason, "spam")
        self.assertEqual(complaint.message, "Yangilangan izoh.")

    def test_update_complaint_invalid_data(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.put(
            f"{self.url}{complaint.id}/",
            {
                "to_user": str(self.user1.id),
                "reason": "spam",
                "message": "Noto'g'ri update.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_complaint_forbidden(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.put(
            f"{self.url}{complaint.id}/",
            {
                "to_user": str(self.user3.id),
                "reason": "spam",
                "message": "Urinish.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_complaint_success(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
            message="Eski izoh.",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"{self.url}{complaint.id}/",
            {
                "message": "Qisman yangilangan izoh.",
                "admin_note": "Qisman tuzatildi.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        complaint.refresh_from_db()
        self.assertEqual(complaint.message, "Qisman yangilangan izoh.")
        self.assertEqual(complaint.admin_note, "Qisman tuzatildi.")

    def test_partial_update_complaint_invalid_data(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"{self.url}{complaint.id}/",
            {"status": "approved"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_update_complaint_forbidden(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.patch(
            f"{self.url}{complaint.id}/",
            {"message": "Ruxsatsiz yangilash."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_decision_complaint_success(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="threat",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"{self.url}{complaint.id}/decision/",
            {
                "decision": "approved",
                "enforcement_action": "warn",
                "admin_note": "Shikoyat asosli deb topildi.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, ComplaintStatus.APPROVED)
        self.assertEqual(complaint.enforcement_action, "warn")
        self.assertEqual(complaint.resolved_by, self.admin)
        self.assertIsNotNone(complaint.resolved_at)

    def test_decision_complaint_approve_with_warn_sends_notification_success(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="abusive_language",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"{self.url}{complaint.id}/decision/",
            {"decision": "approved", "enforcement_action": "warn"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user2.refresh_from_db()
        self.assertFalse(self.user2.is_blocked)
        self.assertTrue(
            Notification.objects.filter(user=self.user2, title="Ogohlantirish").exists()
        )

    @patch("apps.core.utils.face.register_user_faces_as_blocked")
    def test_decision_complaint_approve_with_block_blocks_user_success(
        self, mock_register
    ):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"{self.url}{complaint.id}/decision/",
            {"decision": "approved", "enforcement_action": "block"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user2.refresh_from_db()
        self.assertTrue(self.user2.is_blocked)
        mock_register.assert_called_once()

    def test_decision_complaint_approve_without_enforcement_action_invalid_data(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"{self.url}{complaint.id}/decision/",
            {"decision": "approved"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decision_complaint_reject_without_admin_note_invalid_data(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"{self.url}{complaint.id}/decision/",
            {"decision": "rejected"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decision_complaint_reject_with_short_admin_note_invalid_data(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"{self.url}{complaint.id}/decision/",
            {"decision": "rejected", "admin_note": "qisqa"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decision_complaint_reject_with_too_long_admin_note_invalid_data(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"{self.url}{complaint.id}/decision/",
            {"decision": "rejected", "admin_note": "a" * 501},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decision_complaint_reject_with_valid_admin_note_success(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"{self.url}{complaint.id}/decision/",
            {
                "decision": "rejected",
                "admin_note": "Dalillar yetarli emas, skrinshot mos kelmadi.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, ComplaintStatus.REJECTED)
        self.assertIsNone(complaint.enforcement_action)

    def test_retrieve_complaint_includes_questionnaire_progress_success(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="fraud",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f"{self.url}{complaint.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("questionnaire_progress", response.data["profile_snapshot"])

    def test_decision_complaint_invalid_data(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="threat",
            status=ComplaintStatus.APPROVED,
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"{self.url}{complaint.id}/decision/",
            {
                "decision": "rejected",
                "admin_note": "Qayta ko'rib chiqish urinishi.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decision_complaint_forbidden(self):
        complaint = Complaint.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            reason="threat",
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            f"{self.url}{complaint.id}/decision/",
            {"decision": "approved"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ComplaintQuestionnaireProgressTestCase(TestCase):
    def setUp(self):
        self.role = Role.objects.filter(is_default=True).first()

    def test_get_questionnaire_progress_returns_zero_when_no_profile(self):
        user = User.objects.create(
            phone_number="+998901100050",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )

        result = get_questionnaire_progress(user)

        self.assertEqual(result, {"answered": 0, "total": 0, "percentage": 0})

    def test_get_questionnaire_progress_calculates_role_based_total_success(self):
        user = User.objects.create(
            phone_number="+998901100051",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        profile = Profile.objects.create(
            user=user,
            first_name="Anvar",
            last_name="Karimov",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.GROOM,
            birth_date="1994-05-01",
            height=180,
        )
        section = SectionType.objects.create(name="Umumiy")
        groom_question = Question.objects.create(
            section=section,
            text="Faqat kuyov uchun savol",
            target_gender=TargetGender.GROOM,
            order=1,
        )
        all_question = Question.objects.create(
            section=section,
            text="Barcha uchun savol",
            target_gender=TargetGender.ALL,
            order=2,
        )
        Question.objects.create(
            section=section,
            text="Faqat kelin uchun savol",
            target_gender=TargetGender.BRIDE,
            order=3,
        )
        groom_option = QuestionOption.objects.create(
            question=groom_question, option_letter="A", text="Variant A", weight=5
        )
        UserAnswer.objects.create(
            profile=profile, question=groom_question, selected_option=groom_option
        )

        result = get_questionnaire_progress(user)

        self.assertEqual(result["answered"], 1)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["percentage"], 50)
        self.assertIsNotNone(all_question)


class ComplaintAiAnalysisTestCase(TestCase):
    def setUp(self):
        self.role = Role.objects.filter(is_default=True).first()
        self.from_user = User.objects.create(
            phone_number="+998901100060",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.to_user = User.objects.create(
            phone_number="+998901100061",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )

    def test_build_ai_analysis_low_risk_for_first_time_complaint(self):
        complaint = Complaint.objects.create(
            from_user=self.from_user, to_user=self.to_user, reason="spam"
        )

        result = build_ai_analysis(complaint)

        self.assertEqual(result["risk_level"], "Past")
        self.assertEqual(result["complaints_count"], 0)
        self.assertEqual(result["previous_warnings_count"], 0)
        self.assertEqual(result["recommended_action"], "Qo'shimcha tekshiruv")

    def test_build_ai_analysis_medium_risk_when_only_warning_exists(self):
        Complaint.objects.create(
            from_user=self.from_user,
            to_user=self.to_user,
            reason="spam",
            status=ComplaintStatus.APPROVED,
            enforcement_action="warn",
        )
        complaint = Complaint.objects.create(
            from_user=self.from_user, to_user=self.to_user, reason="fraud"
        )

        result = build_ai_analysis(complaint)

        self.assertEqual(result["risk_level"], "O'rta")
        self.assertEqual(result["complaints_count"], 1)
        self.assertEqual(result["previous_warnings_count"], 1)
        self.assertEqual(result["recommended_action"], "Ogohlantirish yuborish")

    def test_build_ai_analysis_high_risk_when_previous_block_exists(self):
        Complaint.objects.create(
            from_user=self.from_user,
            to_user=self.to_user,
            reason="fraud",
            status=ComplaintStatus.APPROVED,
            enforcement_action="block",
        )
        complaint = Complaint.objects.create(
            from_user=self.from_user, to_user=self.to_user, reason="threat"
        )

        result = build_ai_analysis(complaint)

        self.assertEqual(result["risk_level"], "Yuqori")
        self.assertEqual(result["recommended_action"], "Profilni bloklash")

    def test_build_ai_analysis_complaints_count_includes_all_statuses(self):
        Complaint.objects.create(
            from_user=self.from_user,
            to_user=self.to_user,
            reason="spam",
            status=ComplaintStatus.REJECTED,
        )
        Complaint.objects.create(
            from_user=self.from_user,
            to_user=self.to_user,
            reason="fraud",
            status=ComplaintStatus.PENDING,
        )
        complaint = Complaint.objects.create(
            from_user=self.from_user, to_user=self.to_user, reason="threat"
        )

        result = build_ai_analysis(complaint)

        self.assertEqual(result["complaints_count"], 2)
        self.assertEqual(result["previous_warnings_count"], 0)
