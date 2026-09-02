from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.profiles.models import CandidateRole, GenderType, Profile
from apps.accounts.users.models import AuthProvider, Role, User
from apps.matches.photo_requests.models import PhotoRequest, PhotoRequestStatus


class PhotoRequestTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.filter(is_default=True).first()
        self.url = "/api/v1/matches/photo-requests/"

        self.user1, self.profile1 = self._make_user(
            "+998901111111", GenderType.MALE, CandidateRole.GROOM
        )
        self.user2, self.profile2 = self._make_user(
            "+998902222222", GenderType.FEMALE, CandidateRole.BRIDE
        )

    def _make_user(self, phone, gender, candidate_type):
        """Test uchun foydalanuvchi va uning anketasini yaratadi."""
        user = User.objects.create(
            phone_number=phone,
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        profile = Profile.objects.create(
            user=user,
            first_name="Test",
            last_name="Test",
            gender=gender,
            candidate_type=candidate_type,
            birth_date="1995-01-01",
            height=175,
        )
        return user, profile

    def test_create_photo_request_success(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            self.url, {"to_profile": str(self.profile2.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            PhotoRequest.objects.filter(
                from_profile=self.profile1, to_profile=self.profile2
            ).exists()
        )

    def test_create_photo_request_unauthenticated(self):
        response = self.client.post(
            self.url, {"to_profile": str(self.profile2.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_photo_request_to_self(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            self.url, {"to_profile": str(self.profile1.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_duplicate_pending_request(self):
        PhotoRequest.objects.create(
            from_profile=self.profile1, to_profile=self.profile2
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            self.url, {"to_profile": str(self.profile2.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accept_photo_request_success(self):
        photo_req = PhotoRequest.objects.create(
            from_profile=self.profile1, to_profile=self.profile2
        )
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(f"{self.url}{photo_req.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        photo_req.refresh_from_db()
        self.assertEqual(photo_req.status, PhotoRequestStatus.ACCEPTED)

    def test_accept_photo_request_forbidden(self):
        photo_req = PhotoRequest.objects.create(
            from_profile=self.profile1, to_profile=self.profile2
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(f"{self.url}{photo_req.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reject_photo_request_success(self):
        photo_req = PhotoRequest.objects.create(
            from_profile=self.profile1, to_profile=self.profile2
        )
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(f"{self.url}{photo_req.id}/reject/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        photo_req.refresh_from_db()
        self.assertEqual(photo_req.status, PhotoRequestStatus.REJECTED)

    def test_cannot_decide_already_decided_request(self):
        photo_req = PhotoRequest.objects.create(
            from_profile=self.profile1,
            to_profile=self.profile2,
            status=PhotoRequestStatus.REJECTED,
        )
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(f"{self.url}{photo_req.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_outsider_cannot_see_requests(self):
        other_user, _ = self._make_user(
            "+998903333333", GenderType.MALE, CandidateRole.GROOM
        )
        PhotoRequest.objects.create(
            from_profile=self.profile1, to_profile=self.profile2
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
