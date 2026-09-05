from datetime import timedelta

from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.notifications.models import Notification
from apps.accounts.profiles.models import (
    CandidateRole,
    GenderType,
    Profile,
    RepresentativeInfo,
)
from apps.accounts.questionnaire.models import (
    Question,
    QuestionOption,
    SectionType,
    TargetGender,
    UserAnswer,
)
from apps.accounts.users.models import AuthProvider, Role, User


class PhoneAuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/accounts/auth/phone/"

    def test_phone_auth_creates_user_and_returns_tokens(self):
        response = self.client.post(
            self.url, {"phone_number": "+998901234567"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify custom renderer structure or standard DRF response structure
        data = (
            response.data.get("data", response.data)
            if isinstance(response.data, dict) and "data" in response.data
            else response.data
        )
        self.assertIn("tokens", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["phone_number"], "+998901234567")

        user = User.objects.get(phone_number="+998901234567")
        self.assertFalse(user.is_blocked)

    def test_invalid_phone_returns_400(self):
        invalid_numbers = [
            "901234567",
            "+9989012345",
            "+99890123456789",
            "998901234567",
            "+7901234567",
            "",
        ]
        for number in invalid_numbers:
            with self.subTest(phone=number):
                res = self.client.post(
                    self.url, {"phone_number": number}, format="json"
                )
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_blocked_phone_user_returns_403(self):
        blocked_user = User.objects.create(
            phone_number="+998909999999",
            auth_provider=AuthProvider.PHONE,
            is_blocked=True,
        )
        response = self.client.post(
            self.url, {"phone_number": "+998909999999"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reactivate_deleted_user_resets_profile(self):
        user = User.objects.create(
            phone_number="+998901112233",
            auth_provider=AuthProvider.PHONE,
            is_active=False,
        )

        profile = Profile.objects.create(
            user=user,
            first_name="Eski",
            last_name="Profil",
            birth_date="1995-01-01",
            height=175,
            gender="male",
        )

        response = self.client.post(
            self.url, {"phone_number": "+998901112233"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertFalse(Profile.objects.filter(user=user).exists())


class EmailAuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/accounts/auth/email/"

    def test_email_registration_creates_new_user(self):
        response = self.client.post(
            self.url, {"email": "testuser@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = (
            response.data.get("data", response.data)
            if isinstance(response.data, dict) and "data" in response.data
            else response.data
        )
        self.assertIn("tokens", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], "testuser@example.com")
        self.assertEqual(data["user"]["auth_provider"], AuthProvider.EMAIL)

        user = User.objects.get(email="testuser@example.com")
        self.assertEqual(user.auth_provider, AuthProvider.EMAIL)

    def test_invalid_email_returns_400(self):
        response = self.client.post(self.url, {"email": "not-an-email"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RoleDeleteTestCase(TestCase):
    def setUp(self):
        self.default_role = Role.objects.create(
            name="Default Role Test", is_default=True
        )
        self.normal_role = Role.objects.create(
            name="Normal Role Test", is_default=False
        )

    def test_default_role_delete_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.default_role.delete()

    def test_default_role_hard_delete_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.default_role.hard_delete()

    def test_non_default_role_can_be_deleted(self):
        self.normal_role.delete()
        self.normal_role.refresh_from_db()
        self.assertFalse(self.normal_role.is_active)


class RoleAndPermissionApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(
            phone_number="+998900000001",
            auth_provider=AuthProvider.PHONE,
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(self.admin)

    def test_role_detail_returns_permissions_and_permissions_info(self):
        permission = Permission.objects.get(codename="view_role")
        role = Role.objects.create(name="Content Moderator")
        role.permissions.add(permission)

        response = self.client.get(f"/api/v1/accounts/roles/{role.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data", response.data)
        self.assertEqual(data["permissions"], [permission.id])
        self.assertEqual(len(data["permissions_info"]), 1)
        self.assertEqual(data["permissions_info"][0]["id"], permission.id)
        self.assertEqual(data["permissions_info"][0]["codename"], "view_role")
        self.assertEqual(data["permissions_info"][0]["model_name"], "role")

    def test_permissions_list_returns_group_metadata(self):
        response = self.client.get("/api/v1/accounts/permissions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data", response.data)
        self.assertIn("role", data)
        self.assertEqual(data["role"]["model_name"], "role")
        self.assertIn("group_label", data["role"])
        self.assertIn("permissions", data["role"])
        self.assertTrue(
            any(item["codename"] == "view_role" for item in data["role"]["permissions"])
        )


class AdminUserDetailGuardianTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(
            phone_number="+998900000010",
            auth_provider=AuthProvider.PHONE,
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(self.admin)

        self.role = Role.objects.filter(is_default=True).first()
        self.candidate = User.objects.create(
            phone_number="+998900000011",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        Profile.objects.create(
            user=self.candidate,
            first_name="Nomzod",
            last_name="Test",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.GROOM,
            birth_date="1996-01-01",
            height=180,
        )
        self.rep_user = User.objects.create(
            phone_number="+998900000012",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.rep_profile = Profile.objects.create(
            user=self.rep_user,
            first_name="Vakil",
            last_name="Otasi",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.REPRESENTATIVE,
            birth_date="1970-01-01",
            height=175,
        )

    def _detail(self, user):
        """Berilgan foydalanuvchining admin detail javobini (data, response) qaytaradi."""
        response = self.client.get(f"/api/v1/accounts/users/{user.id}/")
        data = response.data
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        return response, data

    def test_detail_returns_latest_guardian_without_photo(self):
        RepresentativeInfo.objects.create(
            profile=self.rep_profile,
            candidate_role=CandidateRole.GROOM,
            target_candidate=self.candidate,
        )

        response, data = self._detail(self.candidate)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        guardian = data["guardian"]
        self.assertIsNotNone(guardian)
        self.assertEqual(guardian["name"], "Vakil Otasi")
        self.assertEqual(guardian["phone"], "+998900000012")
        self.assertEqual(guardian["candidates_count"], 1)
        self.assertIn("dates", guardian)
        self.assertNotIn("photo", guardian)
        self.assertNotIn("main_photo", guardian)

    def test_detail_returns_most_recent_when_multiple_guardians(self):
        older_rep_user = User.objects.create(
            phone_number="+998900000013",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        older_profile = Profile.objects.create(
            user=older_rep_user,
            first_name="Eski",
            last_name="Vakil",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.REPRESENTATIVE,
            birth_date="1965-01-01",
            height=170,
        )
        old_rep = RepresentativeInfo.objects.create(
            profile=older_profile,
            candidate_role=CandidateRole.GROOM,
            target_candidate=self.candidate,
        )
        RepresentativeInfo.objects.filter(pk=old_rep.pk).update(
            created_at=old_rep.created_at - timedelta(days=1)
        )
        new_rep = RepresentativeInfo.objects.create(
            profile=self.rep_profile,
            candidate_role=CandidateRole.GROOM,
            target_candidate=self.candidate,
        )

        response, data = self._detail(self.candidate)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["guardian"]["id"], str(new_rep.id))
        self.assertEqual(data["guardian"]["name"], "Vakil Otasi")

    def test_detail_guardian_null_when_no_representative(self):
        response, data = self._detail(self.candidate)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(data["guardian"])

    def test_represented_users_endpoint_removed_returns_404(self):
        response = self.client.get(
            f"/api/v1/accounts/users/{self.candidate.id}/represented-users/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class UserListHasRepresentativeFilterTestCase(TestCase):
    """`GET /api/v1/accounts/users/?has_representative=` filtri testi."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(
            phone_number="+998900000020",
            auth_provider=AuthProvider.PHONE,
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(self.admin)
        self.role = Role.objects.filter(is_default=True).first()

        # Vakili bor nomzod.
        self.with_rep = User.objects.create(
            phone_number="+998900000021",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        Profile.objects.create(
            user=self.with_rep,
            first_name="Vakilli",
            last_name="Nomzod",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.GROOM,
            birth_date="1996-01-01",
            height=180,
        )
        rep_user = User.objects.create(
            phone_number="+998900000022",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        rep_profile = Profile.objects.create(
            user=rep_user,
            first_name="Vakil",
            last_name="Otasi",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.REPRESENTATIVE,
            birth_date="1970-01-01",
            height=175,
        )
        RepresentativeInfo.objects.create(
            profile=rep_profile,
            candidate_role=CandidateRole.GROOM,
            target_candidate=self.with_rep,
        )

        # Vakili yo'q nomzod.
        self.without_rep = User.objects.create(
            phone_number="+998900000023",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        Profile.objects.create(
            user=self.without_rep,
            first_name="Yolg'iz",
            last_name="Nomzod",
            gender=GenderType.FEMALE,
            candidate_type=CandidateRole.BRIDE,
            birth_date="1998-01-01",
            height=165,
        )

    def _ids(self, response):
        results = response.data.get("data", response.data)
        if isinstance(results, dict):
            results = results.get("results", [])
        return {str(row["id"]) for row in results}

    def test_has_representative_true_returns_only_candidates_with_representative(self):
        response = self.client.get("/api/v1/accounts/users/?has_representative=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self._ids(response)
        self.assertIn(str(self.with_rep.id), ids)
        self.assertNotIn(str(self.without_rep.id), ids)

    def test_has_representative_false_excludes_candidates_with_representative(self):
        response = self.client.get("/api/v1/accounts/users/?has_representative=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self._ids(response)
        self.assertNotIn(str(self.with_rep.id), ids)
        self.assertIn(str(self.without_rep.id), ids)

    def test_list_unauthenticated_returns_401(self):
        self.client.force_authenticate(None)
        response = self.client.get("/api/v1/accounts/users/?has_representative=true")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminUserHistoryTestCase(TestCase):
    """`GET /api/v1/accounts/users/{id}/history/` testlari."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(
            phone_number="+998900000030",
            auth_provider=AuthProvider.PHONE,
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(self.admin)

        self.role = Role.objects.filter(is_default=True).first()
        self.candidate = User.objects.create(
            phone_number="+998900000031",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile = Profile.objects.create(
            user=self.candidate,
            first_name="Nomzod",
            last_name="Tarix",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.GROOM,
            birth_date="1996-01-01",
            height=180,
        )

        section = SectionType.objects.create(name="Umumiy")
        # Kuyov nomzodga faqat "all" va "groom" savollar tegishli — "bride"
        # savoli maxrajga kirmasligi kerak.
        self.common_questions = [
            Question.objects.create(
                section=section,
                text=f"Umumiy savol {i}",
                target_gender=TargetGender.ALL,
                order=i,
            )
            for i in range(1, 3)
        ]
        self.groom_question = Question.objects.create(
            section=section,
            text="Kuyov savoli",
            target_gender=TargetGender.GROOM,
            order=3,
        )
        self.bride_question = Question.objects.create(
            section=section,
            text="Kelin savoli",
            target_gender=TargetGender.BRIDE,
            order=4,
        )
        for question in [
            *self.common_questions,
            self.groom_question,
            self.bride_question,
        ]:
            QuestionOption.objects.create(
                question=question, option_letter="A", text="A varianti", weight=5
            )

    def _history(self, user):
        """Berilgan foydalanuvchi uchun tarix voqealari ro'yxatini qaytaradi."""
        response = self.client.get(f"/api/v1/accounts/users/{user.id}/history/")
        return response, response.data

    def _questionnaire_event(self, events):
        return next(
            (e for e in events if e["event_type"] == "questionnaire_done"), None
        )

    def test_history_success_counts_only_role_relevant_questions(self):
        option = self.common_questions[0].options.first()
        UserAnswer.objects.create(
            profile=self.profile,
            question=self.common_questions[0],
            selected_option=option,
        )

        response, events = self._history(self.candidate)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = self._questionnaire_event(events)
        self.assertIsNotNone(event)
        # Kuyovga tegishli savollar: 2 ta umumiy + 1 ta kuyov = 3 ta
        # ("bride" savoli hisobga kirmaydi).
        self.assertEqual(event["label"], "Anketa 1/3 yakunlandi")
        self.assertFalse(event["is_done"])

    def test_history_marks_done_when_all_relevant_questions_answered(self):
        for question in [*self.common_questions, self.groom_question]:
            UserAnswer.objects.create(
                profile=self.profile,
                question=question,
                selected_option=question.options.first(),
            )

        response, events = self._history(self.candidate)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = self._questionnaire_event(events)
        self.assertEqual(event["label"], "Anketa 3/3 yakunlandi")
        self.assertTrue(event["is_done"])

    def test_history_omits_questionnaire_event_when_no_answers(self):
        response, events = self._history(self.candidate)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(self._questionnaire_event(events))
        self.assertTrue(any(e["event_type"] == "profile_created" for e in events))

    def test_history_unauthenticated_returns_401(self):
        self.client.force_authenticate(None)
        response = self.client.get(
            f"/api/v1/accounts/users/{self.candidate.id}/history/"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_history_forbidden_for_user_without_permission(self):
        self.client.force_authenticate(self.candidate)
        response = self.client.get(
            f"/api/v1/accounts/users/{self.candidate.id}/history/"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminUserUnblockTestCase(TestCase):
    """`POST /api/v1/accounts/users/{id}/unblock/` testlari."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(
            phone_number="+998900000040",
            auth_provider=AuthProvider.PHONE,
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(self.admin)

        self.role = Role.objects.filter(is_default=True).first()
        self.blocked_user = User.objects.create(
            phone_number="+998900000041",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
            is_blocked=True,
        )
        self.url = f"/api/v1/accounts/users/{self.blocked_user.id}/unblock/"

    def test_unblock_user_success(self):
        response = self.client.post(self.url, {"reason": "mistake"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.blocked_user.refresh_from_db()
        self.assertFalse(self.blocked_user.is_blocked)

    def test_unblock_user_without_reason_invalid(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.blocked_user.refresh_from_db()
        self.assertTrue(self.blocked_user.is_blocked)

    def test_unblock_user_with_notify_sends_notification(self):
        response = self.client.post(
            self.url,
            {"reason": "appeal_accepted", "notify_user": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.filter(user=self.blocked_user).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, "Profilingiz blokdan chiqarildi")
        self.assertIn("Apellyatsiya qabul qilindi", notification.message)

    def test_unblock_user_without_notify_does_not_send_notification(self):
        response = self.client.post(self.url, {"reason": "mistake"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Notification.objects.filter(user=self.blocked_user).exists())

    def test_unblock_user_unauthenticated_returns_401(self):
        self.client.force_authenticate(None)
        response = self.client.post(self.url, {"reason": "mistake"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unblock_user_forbidden_for_user_without_permission(self):
        self.client.force_authenticate(self.blocked_user)
        response = self.client.post(self.url, {"reason": "mistake"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminProfileTestCase(TestCase):
    """Admin panelga kiruvchi xodimning o'z profilini (staff/me/) ko'rish/tahrirlash testlari."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/accounts/staff/me/"
        self.admin = User.objects.create(
            phone_number="+998900000020",
            auth_provider=AuthProvider.PHONE,
            first_name="Abdulaziz",
            last_name="Muxtorov",
            is_staff=True,
            is_superuser=True,
        )

        self.default_role = Role.objects.filter(is_default=True).first()
        self.candidate = User.objects.create(
            phone_number="+998900000021",
            auth_provider=AuthProvider.PHONE,
            role=self.default_role,
        )

    def test_get_admin_profile_success(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data", response.data)
        self.assertEqual(data["first_name"], "Abdulaziz")
        self.assertEqual(data["last_name"], "Muxtorov")
        self.assertEqual(data["phone_number"], "+998900000020")
        self.assertIn("login", data)
        self.assertIn("permissions_summary", data)
        self.assertIn("created_at", data)

    def test_update_admin_profile_success(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            self.url,
            {
                "first_name": "Aziz",
                "last_name": "Sodiqov",
                "phone_number": "+998901112233",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.first_name, "Aziz")
        self.assertEqual(self.admin.last_name, "Sodiqov")
        self.assertEqual(self.admin.phone_number, "+998901112233")

    def test_update_admin_profile_invalid_data_returns_400(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, {"phone_number": "901234567"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_profile_unauthenticated_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_profile_forbidden_for_candidate_returns_403(self):
        self.client.force_authenticate(self.candidate)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
