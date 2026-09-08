from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.complaints.models import Complaint, ComplaintStatus
from apps.accounts.profiles.models import CandidateRole, GenderType, Profile
from apps.accounts.questionnaire.models import Question, SectionType, TargetGender
from apps.accounts.users.models import AuthProvider, Role, User
from apps.consulting.psychologists.models import Psychologist
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

        # ochiq shikoyatlar va AI signallari sidebar badge'iga koʻchdi —
        # summary `tasks` blokida takrorlanmaydi
        self.assertNotIn("complaints_open", data["tasks"])
        self.assertNotIn("ai_signals", data["tasks"])

        # hali modeli yoʻq koʻrsatkichlar
        self.assertEqual(data["totals"]["married"]["value"], 0)
        self.assertIsNone(data["totals"]["married"]["delta_month"])
        self.assertEqual(data["tasks"]["profile_moderation"], 0)

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


@override_settings(CACHES=LOCMEM_CACHE)
class SidebarBadgesApiTestCase(TestCase):
    url = "/api/v1/dashboard/sidebar/"

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.role = Role.objects.filter(is_default=True).first()

        self.user = User.objects.create(
            phone_number="+998901300001",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.staff = User.objects.create(
            phone_number="+998901300010",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
            is_staff=True,
        )

        # 2 ta ochiq (PENDING) + 1 ta yopilgan shikoyat
        Complaint.objects.create(
            from_user=self.user,
            to_user=self.staff,
            reason="spam",
            status=ComplaintStatus.PENDING,
        )
        Complaint.objects.create(
            from_user=self.user,
            to_user=self.staff,
            reason="spam",
            status=ComplaintStatus.PENDING,
        )
        Complaint.objects.create(
            from_user=self.user,
            to_user=self.staff,
            reason="spam",
            status=ComplaintStatus.APPROVED,
        )

        # 3 ta faol + 1 ta nofaol savol → badge 3 chiqishi kerak
        section = SectionType.objects.create(name="Umumiy")
        for i in range(3):
            Question.objects.create(
                section=section, text=f"Savol {i}", target_gender=TargetGender.ALL
            )
        Question.objects.create(
            section=section,
            text="Nofaol",
            target_gender=TargetGender.ALL,
            is_active=False,
        )

    def test_sidebar_success(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        # xodim jami foydalanuvchilar sanogʻiga kirmaydi
        self.assertEqual(data["users"], 1)
        self.assertEqual(data["complaints_open"], 2)
        self.assertEqual(data["questions"], 3)
        # hali modeli yoʻq koʻrsatkich
        self.assertEqual(data["ai_signals"], 0)
        # setUp da psixolog yaratilmagan
        self.assertEqual(data["psychologists"], 0)

    def test_sidebar_counts_only_available_psychologists(self):
        Psychologist.objects.create(
            first_name="Dilshod",
            last_name="Rasulov",
            phone_number="+998911110001",
            specialization="Oila psixologi",
            experience_years=12,
            price=150000,
            session_duration_minutes=50,
            is_available=True,
        )
        Psychologist.objects.create(
            first_name="Sherzod",
            last_name="Aliyev",
            phone_number="+998911110002",
            specialization="Kognitiv terapiya",
            experience_years=15,
            price=200000,
            session_duration_minutes=60,
            is_available=False,
        )
        cache.clear()
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["psychologists"], 1)

    def test_sidebar_unauthenticated(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sidebar_forbidden(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
