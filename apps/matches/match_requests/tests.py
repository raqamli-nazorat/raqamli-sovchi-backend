from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.matches.match_requests.models import MatchRequest, MatchStatus
from apps.accounts.profiles.models import Profile, GenderType, CandidateRole
from apps.accounts.users.models import User, AuthProvider, Role


class MatchRequestsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(name="User", is_default=True)

        self.user1 = User.objects.create(
            phone_number="+998901111111",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile1 = Profile.objects.create(
            user=self.user1,
            first_name="Kuyov",
            last_name="Test",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.GROOM,
            birth_year=1995,
            height=175,
        )

        self.user2 = User.objects.create(
            phone_number="+998902222222",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile2 = Profile.objects.create(
            user=self.user2,
            first_name="Kelin",
            last_name="Test",
            gender=GenderType.FEMALE,
            candidate_type=CandidateRole.BRIDE,
            birth_year=1997,
            height=165,
        )

        self.url = "/api/v1/matches/requests/"

    def test_create_match_request(self):
        self.client.force_authenticate(user=self.user1)
        data = {"to_profile": str(self.profile2.id)}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        match_req = MatchRequest.objects.filter(
            from_profile=self.profile1, to_profile=self.profile2
        ).first()
        self.assertIsNotNone(match_req)
        self.assertEqual(match_req.status, MatchStatus.PENDING)

    def test_accept_match_request(self):
        match_req = MatchRequest.objects.create(
            from_profile=self.profile1,
            to_profile=self.profile2,
            status=MatchStatus.PENDING,
        )
        self.client.force_authenticate(user=self.user2)
        accept_url = f"{self.url}{match_req.id}/accept/"
        response = self.client.post(accept_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        match_req.refresh_from_db()
        self.assertEqual(match_req.status, MatchStatus.ACCEPTED)
