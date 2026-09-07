from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.complaints.models import Complaint, ComplaintStatus
from apps.accounts.profiles.models import CandidateRole, GenderType, Profile
from apps.accounts.users.models import AuthProvider, Role, User
from apps.matches.chats.models import ChatRoom, Message
from apps.matches.match_requests.models import MatchRequest, MatchRequestStatus

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=LOCMEM_CACHE)
class DashboardSummaryApiTestCase(TestCase):
    url = "/api/v1/dashboard/summary/"

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.role = Role.objects.filter(is_default=True).first()

        self.u1, self.p1 = self._make_user(
            "+998901200001", GenderType.FEMALE, CandidateRole.BRIDE
        )
        self.u2, self.p2 = self._make_user(
            "+998901200002", GenderType.MALE, CandidateRole.GROOM
        )
        self.u3, self.p3 = self._make_user(
            "+998901200003", GenderType.MALE, CandidateRole.GROOM
        )

        self.staff = User.objects.create(
            phone_number="+998901200010",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
            is_staff=True,
        )

        # 1 ta qabul qilingan moslik + shu moslik ustidan boshlangan suhbat
        self.match = MatchRequest.objects.create(
            from_profile=self.p1,
            to_profile=self.p2,
            status=MatchRequestStatus.ACCEPTED,
        )
        room = ChatRoom.objects.create(match_request=self.match)
        Message.objects.create(chat_room=room, sender=self.u1, content="Salom")

        # 1 tasi ochiq, 1 tasi yopilgan shikoyat
        Complaint.objects.create(
            from_user=self.u1,
            to_user=self.u2,
            reason="spam",
            status=ComplaintStatus.PENDING,
        )
        Complaint.objects.create(
            from_user=self.u2,
            to_user=self.u3,
            reason="spam",
            status=ComplaintStatus.APPROVED,
        )

    def _make_user(self, phone, gender, candidate_type):
        """Test uchun oddiy foydalanuvchi va uning profilini yaratadi."""
        user = User.objects.create(
            phone_number=phone,
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        profile = Profile.objects.create(
            user=user,
            first_name="Test",
            last_name="User",
            gender=gender,
            candidate_type=candidate_type,
            birth_date="1995-01-01",
            height=170,
        )
        return user, profile

    def test_dashboard_success(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # xodim jami foydalanuvchilar sanogʻiga kirmaydi
        self.assertEqual(data["totals"]["users"]["value"], 3)
        self.assertEqual(data["totals"]["users"]["delta_week"], 3)
        self.assertEqual(data["totals"]["profiles_filled"]["value"], 3)
        self.assertEqual(data["totals"]["profiles_filled"]["conversion_pct"], 100)
        self.assertEqual(data["totals"]["active_chats"]["value"], 1)

        # voronka
        self.assertEqual(data["funnel"]["registered"], 3)
        self.assertEqual(data["funnel"]["profile_filled"], 3)
        self.assertEqual(data["funnel"]["questions_done"], 0)
        self.assertEqual(data["funnel"]["request_sent"], 1)
        self.assertEqual(data["funnel"]["chat_started"], 1)

        # ochiq shikoyatlar
        self.assertEqual(data["tasks"]["complaints_open"], 1)

        # hali modeli yoʻq koʻrsatkichlar
        self.assertEqual(data["totals"]["married"]["value"], 0)
        self.assertIsNone(data["totals"]["married"]["delta_month"])
        self.assertEqual(data["tasks"]["profile_moderation"], 0)
        self.assertEqual(data["tasks"]["ai_signals"], 0)

        # dinamika: default 14 kun
        self.assertEqual(len(data["trend"]["days"]), 14)
        self.assertEqual(len(data["trend"]["registrations"]), 14)
        self.assertEqual(sum(data["trend"]["registrations"]), 3)
        self.assertEqual(sum(data["trend"]["matches"]), 1)

    def test_dashboard_custom_days_success(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(self.url, {"days": 7})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["trend"]["days"]), 7)

    def test_dashboard_invalid_days(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(self.url, {"days": 500})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dashboard_unauthenticated(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_forbidden(self):
        self.client.force_authenticate(user=self.u1)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
