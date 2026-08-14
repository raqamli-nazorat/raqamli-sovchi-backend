from django.contrib.gis.geos import Point
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.profiles.models import Profile, GenderType, CandidateRole
from apps.accounts.users.models import User, AuthProvider, Role


class ProfileNearbyTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(name="User", is_default=True)

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
            birth_year=1995,
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
            birth_year=1998,
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
            birth_year=1999,
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

    def test_nearby_custom_radius(self):
        self.client.force_authenticate(user=self.user_main)

        # Radius 1 km (3km near profile should be excluded)
        response_small = self.client.get(f"{self.url}?radius=1")
        self.assertEqual(response_small.status_code, status.HTTP_200_OK)
        results_small = (
            response_small.data.get("results", response_small.data)
            if isinstance(response_small.data, dict)
            else response_small.data
        )
        if isinstance(results_small, dict) and "data" in results_small:
            results_small = results_small["data"]
        ids_small = [item["id"] for item in results_small]
        self.assertNotIn(str(self.profile_near.id), ids_small)

        # Radius 500 km (Both near and far profiles should be included)
        response_large = self.client.get(f"{self.url}?radius=500")
        self.assertEqual(response_large.status_code, status.HTTP_200_OK)
        results_large = (
            response_large.data.get("results", response_large.data)
            if isinstance(response_large.data, dict)
            else response_large.data
        )
        if isinstance(results_large, dict) and "data" in results_large:
            results_large = results_large["data"]
        ids_large = [item["id"] for item in results_large]
        self.assertIn(str(self.profile_near.id), ids_large)
        self.assertIn(str(self.profile_far.id), ids_large)

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
            birth_year=1990,
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
            birth_year=1995,
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
            birth_year=1998,
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
            birth_year=1970,
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

        # Representative representing both a groom and a bride
        RepresentativeInfo.objects.create(
            profile=self.profile_rep,
            candidate_role=CandidateRole.GROOM,
        )
        RepresentativeInfo.objects.create(
            profile=self.profile_rep,
            candidate_role=CandidateRole.BRIDE,
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
            birth_year=1995,
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
            birth_year=1998,
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
        res_unsave = self.client.post(unsave_url)
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
                birth_year=1998,
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
            birth_year=1998,
            height=165,
        )
        res11 = self.client.post(f"/api/v1/accounts/profiles/{p11.id}/save/")
        self.assertEqual(res11.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("10", str(res11.data))
