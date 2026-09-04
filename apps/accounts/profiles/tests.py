from django.contrib.gis.geos import Point
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.profiles.models import CandidateRole, GenderType, Profile
from apps.accounts.users.models import AuthProvider, Role, User


class ProfileNearbyTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        # post_migrate signali yaratgan haqiqiy boshlang'ich rol ishlatiladi —
        # unda oddiy foydalanuvchining real huquqlari bor. Yangi bo'sh rol
        # yaratilsa, u haqiqiysini almashtirib yuboradi va hamma so'rov 403 bo'ladi.
        self.role = Role.objects.filter(is_default=True).first()

        # 1. Main User (Tashkent Center: 41.2995, 69.2401)
        self.user_main = User.objects.create(
            phone_number="+998901111111",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile_main = Profile.objects.create(
            user=self.user_main,
            first_name="Toshkent",
            last_name="Bosh",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.GROOM,
            birth_date="1995-01-01",
            height=175,
            latitude=41.299500,
            longitude=69.240100,
            location=Point(69.240100, 41.299500, srid=4326),
        )

        # 2. Nearby User (~3 km away: Chorsu - 41.3275, 69.2345)
        self.user_near = User.objects.create(
            phone_number="+998902222222",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile_near = Profile.objects.create(
            user=self.user_near,
            first_name="Yaqin",
            last_name="Nomzod",
            gender=GenderType.FEMALE,
            candidate_type=CandidateRole.BRIDE,
            birth_date="1998-01-01",
            height=165,
            latitude=41.327500,
            longitude=69.234500,
            location=Point(69.234500, 41.327500, srid=4326),
        )

        # 3. Far User (~300 km away: Samarkand - 39.6542, 66.9597)
        self.user_far = User.objects.create(
            phone_number="+998903333333",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile_far = Profile.objects.create(
            user=self.user_far,
            first_name="Olis",
            last_name="Nomzod",
            gender=GenderType.FEMALE,
            candidate_type=CandidateRole.BRIDE,
            birth_date="1999-01-01",
            height=168,
            latitude=39.654200,
            longitude=66.959700,
            location=Point(66.959700, 39.654200, srid=4326),
        )

        self.url = "/api/v1/accounts/profiles/nearby/"

    def test_nearby_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nearby_returns_profiles_within_default_radius(self):
        self.client.force_authenticate(user=self.user_main)
        response = self.client.get(self.url)  # default 10km radius
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Extract items if paginated or direct list
        results = (
            response.data.get("results", response.data)
            if isinstance(response.data, dict)
            else response.data
        )
        if isinstance(results, dict) and "data" in results:
            results = results["data"]

        # Should find 'Yaqin Nomzod' (3km) but NOT 'Olis Nomzod' (300km) and NOT self
        ids = [item["id"] for item in results]
        self.assertIn(str(self.profile_near.id), ids)
        self.assertNotIn(str(self.profile_far.id), ids)
        self.assertNotIn(str(self.profile_main.id), ids)

    def test_nearby_custom_radius_filters_correctly(self):
        """Kichik radius (1 km) yaqin profil (3 km)ni chiqarib tashlashini tekshiradi."""
        self.client.force_authenticate(user=self.user_main)
        response = self.client.get(f"{self.url}?radius=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        if isinstance(results, dict) and "data" in results:
            results = results["data"]
        ids = [item["id"] for item in results]
        self.assertNotIn(str(self.profile_near.id), ids)

    def test_nearby_invalid_radius_rejected(self):
        """Ruxsat etilmagan radius qiymati 400 qaytarishini tekshiradi."""
        self.client.force_authenticate(user=self.user_main)
        for bad_radius in [0, 2, 7, 500, -1]:
            with self.subTest(radius=bad_radius):
                response = self.client.get(f"{self.url}?radius={bad_radius}")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nearby_string_radius_rejected(self):
        """Raqam bo'lmagan radius 400 qaytarishini tekshiradi."""
        self.client.force_authenticate(user=self.user_main)
        response = self.client.get(f"{self.url}?radius=abc")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nearby_fails_if_profile_has_no_location(self):
        # User without location
        user_no_loc = User.objects.create(
            phone_number="+998904444444",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        Profile.objects.create(
            user=user_no_loc,
            first_name="Bez",
            last_name="Location",
            gender=GenderType.MALE,
            birth_date="1990-01-01",
            height=180,
        )

        self.client.force_authenticate(user=user_no_loc)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProfileGenderFilterTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(name="User Test Role", is_default=True)
        self.url = "/api/v1/accounts/profiles/"

        # Groom profile
        self.user_groom = User.objects.create(
            phone_number="+998901000001",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile_groom = Profile.objects.create(
            user=self.user_groom,
            first_name="Kuyov",
            last_name="Test",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.GROOM,
            birth_date="1995-01-01",
            height=175,
        )

        # Bride profile
        self.user_bride = User.objects.create(
            phone_number="+998901000002",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile_bride = Profile.objects.create(
            user=self.user_bride,
            first_name="Kelin",
            last_name="Test",
            gender=GenderType.FEMALE,
            candidate_type=CandidateRole.BRIDE,
            birth_date="1998-01-01",
            height=165,
        )

        # Representative profile
        self.user_rep = User.objects.create(
            phone_number="+998901000003",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile_rep = Profile.objects.create(
            user=self.user_rep,
            first_name="Vakil",
            last_name="Test",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.REPRESENTATIVE,
            birth_date="1970-01-01",
            height=170,
        )

    def _get_profile_ids(self, response):
        data = response.data
        results = data.get("results", data) if isinstance(data, dict) else data
        if isinstance(results, dict) and "data" in results:
            results = results["data"]
        return [str(item["id"]) for item in results]

    def test_groom_user_sees_only_brides(self):
        self.client.force_authenticate(user=self.user_groom)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self._get_profile_ids(response)

        self.assertIn(str(self.profile_bride.id), ids)
        self.assertNotIn(str(self.profile_groom.id), ids)
        self.assertNotIn(str(self.profile_rep.id), ids)

    def test_bride_user_sees_only_grooms(self):
        self.client.force_authenticate(user=self.user_bride)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self._get_profile_ids(response)

        self.assertIn(str(self.profile_groom.id), ids)
        self.assertNotIn(str(self.profile_bride.id), ids)
        self.assertNotIn(str(self.profile_rep.id), ids)

    def test_representative_user_for_bride_sees_only_grooms(self):
        from apps.accounts.profiles.models import RepresentativeInfo

        RepresentativeInfo.objects.create(
            profile=self.profile_rep,
            candidate_role=CandidateRole.BRIDE,
        )

        self.client.force_authenticate(user=self.user_rep)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self._get_profile_ids(response)

        self.assertIn(str(self.profile_groom.id), ids)
        self.assertNotIn(str(self.profile_bride.id), ids)
        self.assertNotIn(str(self.profile_rep.id), ids)

    def test_representative_user_for_groom_sees_only_brides(self):
        from apps.accounts.profiles.models import RepresentativeInfo

        RepresentativeInfo.objects.create(
            profile=self.profile_rep,
            candidate_role=CandidateRole.GROOM,
        )

        self.client.force_authenticate(user=self.user_rep)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self._get_profile_ids(response)

        self.assertIn(str(self.profile_bride.id), ids)
        self.assertNotIn(str(self.profile_groom.id), ids)
        self.assertNotIn(str(self.profile_rep.id), ids)

    def test_representative_user_for_both_sees_all_candidates(self):
        from apps.accounts.profiles.models import RepresentativeInfo

        # RepresentativeInfo.profile — OneToOneField, ya'ni bitta vakilga bitta
        # yozuv. Ikkala rolni qamrash uchun yagona yozuvdan foydalaniladi:
        # candidate_role kelinni beradi, biriktirilgan nomzod (target_candidate)
        # esa kuyov bo'lgani uchun filtr ikkinchi rolni ham qo'shadi.
        other_groom_user = User.objects.create(
            phone_number="+998901000004",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        Profile.objects.create(
            user=other_groom_user,
            first_name="Kuyov2",
            last_name="Test",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.GROOM,
            birth_date="1994-01-01",
            height=178,
        )
        RepresentativeInfo.objects.create(
            profile=self.profile_rep,
            candidate_role=CandidateRole.BRIDE,
            target_candidate=other_groom_user,
        )

        self.client.force_authenticate(user=self.user_rep)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self._get_profile_ids(response)

        self.assertIn(str(self.profile_groom.id), ids)
        self.assertIn(str(self.profile_bride.id), ids)
        self.assertNotIn(str(self.profile_rep.id), ids)


class SavedProfileTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(name="User Saved Role", is_default=True)

        self.user1 = User.objects.create(
            phone_number="+998909990001",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile1 = Profile.objects.create(
            user=self.user1,
            first_name="User1",
            last_name="Test",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.GROOM,
            birth_date="1995-01-01",
            height=175,
        )

        self.user2 = User.objects.create(
            phone_number="+998909990002",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile2 = Profile.objects.create(
            user=self.user2,
            first_name="User2",
            last_name="Test",
            gender=GenderType.FEMALE,
            candidate_type=CandidateRole.BRIDE,
            birth_date="1998-01-01",
            height=165,
        )

    def test_save_and_unsave_profile(self):
        self.client.force_authenticate(user=self.user1)

        # 1. Save profile2
        save_url = f"/api/v1/accounts/profiles/{self.profile2.id}/save/"
        res_save = self.client.post(save_url)
        self.assertEqual(res_save.status_code, status.HTTP_200_OK)
        self.assertTrue(res_save.data.get("is_saved"))

        # 2. Check saved list
        saved_list_url = "/api/v1/accounts/profiles/saved/"
        res_list = self.client.get(saved_list_url)
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        data = res_list.data.get("results", res_list.data)
        ids = [item["id"] for item in data]
        self.assertIn(str(self.profile2.id), ids)

        # 3. Unsave profile2
        unsave_url = f"/api/v1/accounts/profiles/{self.profile2.id}/unsave/"
        # unsave amali DELETE usuli bilan e'lon qilingan (views.py: methods=["delete"])
        res_unsave = self.client.delete(unsave_url)
        self.assertEqual(res_unsave.status_code, status.HTTP_200_OK)
        self.assertFalse(res_unsave.data.get("is_saved"))

        # 4. Check saved list again
        res_list_after = self.client.get(saved_list_url)
        data_after = res_list_after.data.get("results", res_list_after.data)
        ids_after = [item["id"] for item in data_after]
        self.assertNotIn(str(self.profile2.id), ids_after)

    def test_cannot_save_own_profile(self):
        self.client.force_authenticate(user=self.user1)
        save_url = f"/api/v1/accounts/profiles/{self.profile1.id}/save/"
        res = self.client.post(save_url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_saved_profiles_max_limit(self):
        self.client.force_authenticate(user=self.user1)

        # Create 10 female profiles and save them
        for i in range(10):
            u = User.objects.create(
                phone_number=f"+9989080000{i:02d}",
                auth_provider=AuthProvider.PHONE,
                role=self.role,
            )
            p = Profile.objects.create(
                user=u,
                first_name=f"Bride_{i}",
                last_name="Test",
                gender=GenderType.FEMALE,
                candidate_type=CandidateRole.BRIDE,
                birth_date="1998-01-01",
                height=165,
            )
            res = self.client.post(f"/api/v1/accounts/profiles/{p.id}/save/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Attempt to save 11th profile
        u11 = User.objects.create(
            phone_number="+998908000099",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        p11 = Profile.objects.create(
            user=u11,
            first_name="Bride_11",
            last_name="Test",
            gender=GenderType.FEMALE,
            candidate_type=CandidateRole.BRIDE,
            birth_date="1998-01-01",
            height=165,
        )
        res11 = self.client.post(f"/api/v1/accounts/profiles/{p11.id}/save/")
        self.assertEqual(res11.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("10", str(res11.data))


class SeedTestCandidatesCommandTestCase(TestCase):
    """`seed_test_candidates` va `unseed_test_candidates` buyruqlari testi."""

    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command

        # Buyruq ma'lumotnoma, tuman va savollarga tayanadi.
        call_command("load_locations")
        call_command("load_references")
        call_command("load_questions")

    def test_seed_creates_full_fergana_profiles_and_unseed_removes_all(self):
        from django.core.management import call_command

        from apps.accounts.profiles.models import Profile, RepresentativeInfo
        from apps.accounts.questionnaire.models import UserAnswer
        from apps.accounts.users.models import User

        call_command("seed_test_candidates", count=12, seed=1)

        users = User.objects.filter(phone_number__startswith="+99890000")
        self.assertEqual(users.count(), 12)

        profiles = Profile.objects.filter(user__in=users)
        self.assertEqual(profiles.count(), 12)
        # Hammasi Farg'ona viloyatiga tegishli.
        self.assertTrue(all("Farg'ona" in p.region.name for p in profiles))
        self.assertTrue(all(p.district_id is not None for p in profiles))
        self.assertTrue(all(p.location is not None for p in profiles))
        self.assertTrue(all(p.photos.exists() for p in profiles))
        self.assertTrue(all(p.answers.exists() for p in profiles))
        self.assertTrue(all(hasattr(u, "pledge") and u.is_verified for u in users))

        # Kamida bitta vakil va u nomzodga biriktirilgan.
        rep_infos = RepresentativeInfo.objects.filter(profile__in=profiles)
        self.assertTrue(rep_infos.exists())
        self.assertTrue(rep_infos.filter(target_candidate__isnull=False).exists())

        call_command("unseed_test_candidates")

        self.assertEqual(
            User.objects.filter(phone_number__startswith="+99890000").count(), 0
        )
        self.assertEqual(UserAnswer.objects.filter(profile__in=profiles).count(), 0)

    def test_seed_is_idempotent_on_repeated_run(self):
        from django.core.management import call_command

        from apps.accounts.users.models import User

        call_command("seed_test_candidates", count=10, seed=1)
        call_command("seed_test_candidates", count=10, seed=2)

        # Ikkinchi ishga tushirish avvalgilarni tozalab, aynan 10 ta qoldiradi.
        self.assertEqual(
            User.objects.filter(phone_number__startswith="+99890000").count(), 10
        )
        call_command("unseed_test_candidates")
