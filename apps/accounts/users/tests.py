from datetime import timedelta

from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.profiles.models import (
    CandidateRole,
    GenderType,
    Profile,
    RepresentativeInfo,
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
