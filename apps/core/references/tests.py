from django.core.management import call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.users.models import AuthProvider, Role, User
from apps.core.references.models import (
    EducationLevel,
    HealthStatus,
    Kinship,
    MaritalStatus,
    Nationality,
    Profession,
)

REFERENCE_MODELS = (
    EducationLevel,
    Profession,
    Nationality,
    MaritalStatus,
    HealthStatus,
    Kinship,
)


class LoadReferencesCommandTestCase(TestCase):
    def test_command_fills_all_reference_tables(self):
        for model in REFERENCE_MODELS:
            self.assertEqual(model.objects.count(), 0)

        call_command("load_references", verbosity=0)

        for model in REFERENCE_MODELS:
            self.assertGreater(
                model.objects.count(), 0, f"{model.__name__} bo'sh qoldi"
            )

    def test_command_is_idempotent(self):
        call_command("load_references", verbosity=0)
        counts = {m: m.objects.count() for m in REFERENCE_MODELS}

        call_command("load_references", verbosity=0)

        for model, expected in counts.items():
            self.assertEqual(
                model.objects.count(), expected, f"{model.__name__} takrorlandi"
            )

    def test_profession_str_returns_name(self):
        profession = Profession.objects.create(name="Dasturchi")
        self.assertEqual(str(profession), "Dasturchi")


class ReferenceEndpointTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        # post_migrate signali yaratgan haqiqiy boshlang'ich rol ishlatiladi.
        self.role = Role.objects.filter(is_default=True).first()
        self.user = User.objects.create(
            phone_number="+998931111111",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        call_command("load_references", verbosity=0)

    def test_user_can_list_professions(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/references/professions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data["count"], 0)

    def test_user_cannot_create_profession(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/references/professions/", {"name": "Yangi kasb"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Profession.objects.filter(name="Yangi kasb").exists())
