from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.profiles.models import CandidateRole, GenderType, Profile
from apps.accounts.users.models import AuthProvider, Role, User
from apps.matches.match_requests.models import MatchRequest, MatchRequestStatus


class MatchRequestsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        # post_migrate signali yaratgan haqiqiy boshlang'ich rol ishlatiladi —
        # unda oddiy foydalanuvchining real huquqlari bor. Yangi bo'sh rol
        # yaratilsa, u haqiqiysini almashtirib yuboradi va hamma so'rov 403 bo'ladi.
        self.role = Role.objects.filter(is_default=True).first()

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

        self.url = "/api/v1/matches/match-requests/"

    def test_create_match_request(self):
        self.client.force_authenticate(user=self.user1)
        data = {"to_profile": str(self.profile2.id)}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        match_req = MatchRequest.objects.filter(
            from_profile=self.profile1, to_profile=self.profile2
        ).first()
        self.assertIsNotNone(match_req)
        self.assertEqual(match_req.status, MatchRequestStatus.PENDING)

    def test_accept_match_request(self):
        match_req = MatchRequest.objects.create(
            from_profile=self.profile1,
            to_profile=self.profile2,
            status=MatchRequestStatus.PENDING,
        )
        self.client.force_authenticate(user=self.user2)
        accept_url = f"{self.url}{match_req.id}/accept/"
        response = self.client.post(accept_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        match_req.refresh_from_db()
        self.assertEqual(match_req.status, MatchRequestStatus.ACCEPTED)


class MatchRequestGuardsTestCase(TestCase):
    """Moslik so'rovi endpointidagi xavfsizlik va mantiqiy himoyalar testlari."""

    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.filter(is_default=True).first()
        self.url = "/api/v1/matches/match-requests/"

        self.groom, self.groom_profile = self._make_user(
            "+998911111111", GenderType.MALE, CandidateRole.GROOM
        )
        self.bride, self.bride_profile = self._make_user(
            "+998912222222", GenderType.FEMALE, CandidateRole.BRIDE
        )
        self.other_groom, self.other_groom_profile = self._make_user(
            "+998913333333", GenderType.MALE, CandidateRole.GROOM
        )

    def _make_user(self, phone, gender, candidate_type):
        """Test uchun foydalanuvchi va uning anketasini yaratadi."""
        user = User.objects.create(
            phone_number=phone, auth_provider=AuthProvider.PHONE, role=self.role
        )
        profile = Profile.objects.create(
            user=user,
            first_name="Test",
            last_name="Test",
            gender=gender,
            candidate_type=candidate_type,
            birth_year=1995,
            height=175,
        )
        return user, profile

    def test_from_profile_taken_from_request_user(self):
        self.client.force_authenticate(user=self.groom)
        response = self.client.post(
            self.url,
            {
                "to_profile": str(self.bride_profile.id),
                "from_profile": str(self.other_groom_profile.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = MatchRequest.objects.get(to_profile=self.bride_profile)
        self.assertEqual(created.from_profile_id, self.groom_profile.id)

    def test_cannot_send_request_to_self(self):
        self.client.force_authenticate(user=self.groom)
        response = self.client.post(
            self.url, {"to_profile": str(self.groom_profile.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_send_request_to_same_gender(self):
        self.client.force_authenticate(user=self.groom)
        response = self.client.post(
            self.url, {"to_profile": str(self.other_groom_profile.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_send_duplicate_pending_request(self):
        MatchRequest.objects.create(
            from_profile=self.groom_profile, to_profile=self.bride_profile
        )
        self.client.force_authenticate(user=self.groom)
        response = self.client.post(
            self.url, {"to_profile": str(self.bride_profile.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_outsider_cannot_see_other_requests(self):
        MatchRequest.objects.create(
            from_profile=self.groom_profile, to_profile=self.bride_profile
        )
        self.client.force_authenticate(user=self.other_groom)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # response.data — renderer o'ramasidan oldingi xom ma'lumot.
        # O'ralgan ko'rinish uchun response.json() ishlatiladi.
        self.assertEqual(response.data["count"], 0)

    def test_status_cannot_be_changed_via_patch(self):
        match_req = MatchRequest.objects.create(
            from_profile=self.groom_profile, to_profile=self.bride_profile
        )
        self.client.force_authenticate(user=self.groom)
        response = self.client.patch(
            f"{self.url}{match_req.id}/", {"status": "accepted"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        match_req.refresh_from_db()
        self.assertEqual(match_req.status, MatchRequestStatus.PENDING)

    def test_invalid_visibility_scope_rejected(self):
        match_req = MatchRequest.objects.create(
            from_profile=self.groom_profile, to_profile=self.bride_profile
        )
        self.client.force_authenticate(user=self.bride)
        response = self.client.post(
            f"{self.url}{match_req.id}/accept/",
            {"visibility_scope": "notogri_qiymat"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        match_req.refresh_from_db()
        self.assertEqual(match_req.status, MatchRequestStatus.PENDING)

    def test_cannot_decide_already_rejected_request(self):
        match_req = MatchRequest.objects.create(
            from_profile=self.groom_profile,
            to_profile=self.bride_profile,
            status=MatchRequestStatus.REJECTED,
        )
        self.client.force_authenticate(user=self.bride)
        response = self.client.post(f"{self.url}{match_req.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_representative_can_decide_forwarded_request(self):
        from apps.accounts.profiles.models import RepresentativeInfo

        rep_user, rep_profile = self._make_user(
            "+998914444444", GenderType.MALE, CandidateRole.REPRESENTATIVE
        )
        RepresentativeInfo.objects.create(
            profile=rep_profile,
            candidate_role="bride",
            target_candidate=self.bride,
            is_approved=True,
        )

        match_req = MatchRequest.objects.create(
            from_profile=self.groom_profile,
            to_profile=self.bride_profile,
            status=MatchRequestStatus.FORWARDED_TO_REPRESENTATIVE,
        )

        self.client.force_authenticate(user=rep_user)
        response = self.client.post(f"{self.url}{match_req.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        match_req.refresh_from_db()
        self.assertEqual(match_req.status, MatchRequestStatus.ACCEPTED)
