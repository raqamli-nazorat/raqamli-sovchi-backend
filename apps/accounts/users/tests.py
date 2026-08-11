from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.users.models import User, AuthProvider



class EmailAuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/accounts/auth/email/"

    def test_email_registration_creates_new_user(self):
        response = self.client.post(
            self.url, {"email": "testuser@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["created"])
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])
        self.assertEqual(response.data["user"]["email"], "testuser@example.com")
        self.assertEqual(response.data["user"]["auth_provider"], AuthProvider.EMAIL)

        user = User.objects.get(email="testuser@example.com")
        self.assertEqual(user.auth_provider, AuthProvider.EMAIL)

    def test_email_login_existing_user(self):
        self.client.post(self.url, {"email": "existing@example.com"}, format="json")

        response = self.client.post(
            self.url, {"email": "EXISTING@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["created"])
        self.assertIn("access", response.data["tokens"])
        self.assertEqual(response.data["user"]["email"], "existing@example.com")

    def test_invalid_email_returns_400(self):
        response = self.client.post(self.url, {"email": "not-an-email"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GoogleAuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/accounts/auth/google/"

    def test_google_auth_requires_code_or_token(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    @patch("apps.accounts.users.views.GoogleOAuth2Adapter")
    def test_google_auth_with_code_creates_user_without_phone(self, mock_adapter_cls):
        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter

        mock_client = MagicMock()
        mock_client.get_access_token.return_value = {
            "access_token": "fake-access-token",
            "id_token": "fake-id-token",
        }
        mock_adapter.get_client.return_value = mock_client
        mock_adapter.provider_id = "google"

        mock_social_login = MagicMock()
        mock_social_login.account.uid = "google-uid-123"
        mock_social_login.account.extra_data = {"email": "googleuser@example.com"}
        mock_social_login.user = User(email="googleuser@example.com")
        mock_adapter.complete_login.return_value = mock_social_login

        response = self.client.post(
            self.url,
            {"code": "sample_auth_code_from_google"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["created"])
        self.assertEqual(response.data["user"]["email"], "googleuser@example.com")
        self.assertIsNone(response.data["user"]["phone_number"])
        self.assertEqual(response.data["user"]["auth_provider"], AuthProvider.GOOGLE)

        user = User.objects.get(email="googleuser@example.com")
        self.assertEqual(user.auth_provider, AuthProvider.GOOGLE)
        self.assertIsNone(user.phone_number)

    @patch("apps.accounts.users.views.GoogleOAuth2Adapter")
    def test_google_auth_with_authorization_code_alias(self, mock_adapter_cls):
        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter

        mock_client = MagicMock()
        mock_client.get_access_token.return_value = {
            "access_token": "fake-access-token"
        }
        mock_adapter.get_client.return_value = mock_client
        mock_adapter.provider_id = "google"

        mock_social_login = MagicMock()
        mock_social_login.account.uid = "google-uid-456"
        mock_social_login.account.extra_data = {"email": "aliasuser@example.com"}
        mock_social_login.user = User(email="aliasuser@example.com")
        mock_adapter.complete_login.return_value = mock_social_login

        response = self.client.post(
            self.url,
            {"authorization_code": "auth_code_alias_123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["created"])
        self.assertEqual(response.data["user"]["email"], "aliasuser@example.com")


from django.core.exceptions import ValidationError
from apps.accounts.users.models import Role


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
