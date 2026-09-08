from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.users.models import AuthProvider, Role, User
from apps.consulting.psychologists.models import Psychologist

LIST_URL = "/api/v1/psychologists/"


def detail_url(pk):
    return f"{LIST_URL}{pk}/"


class PsychologistEndpointTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.default_role = Role.objects.filter(is_default=True).first()
        self.regular_user = User.objects.create(
            phone_number="+998900000000",
            auth_provider=AuthProvider.PHONE,
            role=self.default_role,
        )
        self.staff_user = User.objects.create(
            phone_number="+998900000001",
            auth_provider=AuthProvider.PHONE,
            is_staff=True,
            is_superuser=True,
        )
        self.psychologist = Psychologist.objects.create(
            first_name="Dilshod",
            last_name="Rasulov",
            phone_number="+998911112233",
            specialization="Oila psixologi",
            experience_years=12,
            price=150000,
            session_duration_minutes=50,
        )
        self.valid_payload = {
            "first_name": "Nargiza",
            "last_name": "Yo'ldosheva",
            "phone_number": "+998911112244",
            "specialization": "Nikohga tayyorgarlik",
            "experience_years": 8,
            "price": 120000,
            "session_duration_minutes": 50,
            "is_available": True,
        }

    def test_list_success(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_unauthenticated(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_forbidden_for_regular_user(self):
        self.client.force_authenticate(self.regular_user)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_success(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(LIST_URL, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Psychologist.objects.filter(phone_number="+998911112244").exists()
        )

    def test_create_duplicate_phone_invalid_data(self):
        self.client.force_authenticate(self.staff_user)
        payload = {**self.valid_payload, "phone_number": "+998911112233"}
        response = self.client.post(LIST_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_unauthenticated(self):
        response = self.client.post(LIST_URL, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_success(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.get(detail_url(self.psychologist.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_toggles_availability(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.patch(
            detail_url(self.psychologist.id),
            {"is_available": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.psychologist.refresh_from_db()
        self.assertFalse(self.psychologist.is_available)

    def test_update_invalid_price(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.patch(
            detail_url(self.psychologist.id), {"price": 0}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_soft_deletes(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.delete(detail_url(self.psychologist.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.psychologist.refresh_from_db()
        self.assertFalse(self.psychologist.is_active)

    def test_full_name_property_joins_first_and_last(self):
        self.assertEqual(self.psychologist.full_name, "Dilshod Rasulov")
