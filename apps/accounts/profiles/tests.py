from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.profiles.models import Profile, ProfilePhoto
from apps.accounts.profiles.serializers import (
    ProfileMeSerializer,
    ProfilePhotoSerializer,
    ProfileSerializer,
)
from apps.accounts.users.signals import DEFAULT_PERMISSIONS_CODENAMES
from apps.core.utils.face import verify_profile_photo
from apps.accounts.users.models import User
from apps.accounts.users.serializers import UserSerializer


def image_file(name="photo.jpg", content_type="image/jpeg"):
    content = BytesIO()
    Image.new("RGB", (32, 32), "white").save(content, "JPEG")
    return SimpleUploadedFile(name, content.getvalue(), content_type=content_type)


class ProfileOnboardingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(email="owner@example.com")
        self.other = User.objects.create(email="other@example.com")
        self.user.user_permissions.add(Permission.objects.get(codename="add_profile"))
        self.client.force_authenticate(self.user)

    def profile(self, user=None, **kwargs):
        values = {
            "user": user or self.user,
            "first_name": "Ali",
            "last_name": "Valiyev",
            "gender": "male",
            "candidate_type": "groom",
            "birth_year": 1990,
            "height": 180,
        }
        values.update(kwargs)
        return Profile.objects.create(**values)

    def test_default_role_permission_set_includes_profile_creation_once(self):
        self.assertEqual(DEFAULT_PERMISSIONS_CODENAMES.count("add_profile"), 1)

    def test_profile_create_uses_authenticated_user_and_weight_is_optional(self):
        response = self.client.post(
            "/api/v1/accounts/profiles/",
            {
                "user": str(self.other.id),
                "first_name": "Ali",
                "last_name": "Valiyev",
                "gender": "male",
                "candidate_type": "groom",
                "birth_year": 1990,
                "height": 180,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(Profile.objects.get(user=self.user).weight)

    def test_duplicate_profile_create_is_rejected(self):
        self.profile()
        response = self.client.post(
            "/api/v1/accounts/profiles/",
            {
                "first_name": "Ali",
                "last_name": "Valiyev",
                "gender": "male",
                "candidate_type": "groom",
                "birth_year": 1990,
                "height": 180,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_candidate_gender_contract_and_completion_do_not_require_weight(self):
        invalid = ProfileSerializer(
            data={
                "first_name": "Ali", "last_name": "Valiyev", "gender": "female",
                "candidate_type": "groom", "birth_year": 1990, "height": 180,
            }
        )
        self.assertFalse(invalid.is_valid())
        representative = ProfileSerializer(
            data={
                "first_name": "Ali", "last_name": "Valiyev", "gender": "female",
                "candidate_type": "representative", "birth_year": 1990, "height": 180,
            }
        )
        self.assertTrue(representative.is_valid(), representative.errors)
        self.profile(weight=None)
        self.assertEqual(UserSerializer(self.user).data["completion_percentage"], 60)
        self.assertEqual(UserSerializer(self.user).data["candidate_type"], "groom")

    def test_photo_mime_extension_and_order_are_validated(self):
        serializer = ProfilePhotoSerializer(
            data={"image": image_file("photo.gif", "image/gif"), "order": 5}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("image", serializer.errors)
        self.assertIn("order", serializer.errors)

    def test_voice_intro_accepts_only_small_aac_or_m4a_files(self):
        serializer = ProfileMeSerializer(
            instance=self.profile(),
            data={"voice_intro": SimpleUploadedFile("intro.mp3", b"audio", content_type="audio/mpeg")},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("voice_intro", serializer.errors)

    @patch("apps.accounts.profiles.serializers.verify_profile_photo", return_value=(True, "ok", [0.1]))
    def test_photo_owner_limit_and_main_photo_patch(self, _verify):
        profile = self.profile()
        response = self.client.post(
            "/api/v1/accounts/photos/",
            {"image": image_file("1.jpg"), "order": 1, "is_main": True},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(
            "/api/v1/accounts/photos/", {"image": image_file("duplicate.jpg"), "order": 1}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for order in range(2, 5):
            response = self.client.post(
                "/api/v1/accounts/photos/",
                {"image": image_file(f"{order}.jpg"), "order": order},
                format="multipart",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(
            "/api/v1/accounts/photos/", {"image": image_file("five.jpg")}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        second = profile.photos.get(order=2)
        response = self.client.patch(f"/api/v1/accounts/photos/{second.id}/", {"is_main": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.photos.filter(is_active=True, is_main=True).count(), 1)
        self.assertTrue(profile.photos.get(pk=second.id).is_main)

    def test_photo_query_does_not_expose_another_users_photo(self):
        photo = ProfilePhoto.objects.create(profile=self.profile(user=self.other), image=image_file(), order=1)
        response = self.client.get(f"/api/v1/accounts/photos/{photo.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_face_verification_requires_profile_and_main_photo(self):
        response = self.client.post("/api/v1/accounts/face-verify/", {"image": image_file()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["verified"])
        self.profile()
        response = self.client.post("/api/v1/accounts/face-verify/", {"image": image_file()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["_error_code"], "main_photo_required")

    @patch("apps.accounts.profiles.views.hash_compare", return_value=(True, "ok"))
    @patch("apps.accounts.profiles.views.extract_embedding", return_value=None)
    def test_face_verification_success(self, _embedding, _compare):
        profile = self.profile()
        ProfilePhoto.objects.create(profile=profile, image=image_file(), order=1, is_main=True)
        response = self.client.post("/api/v1/accounts/face-verify/", {"image": image_file()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["verified"])

    @patch("apps.accounts.profiles.views.hash_compare", return_value=(False, "mismatch"))
    @patch("apps.accounts.profiles.views.extract_embedding", return_value=None)
    def test_face_verification_mismatch_is_retryable(self, _embedding, _compare):
        profile = self.profile()
        ProfilePhoto.objects.create(profile=profile, image=image_file(), order=1, is_main=True)
        response = self.client.post("/api/v1/accounts/face-verify/", {"image": image_file()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["verified"])
        self.assertTrue(response.data["retryable"])

    @patch("apps.accounts.profiles.views.register_user_faces_as_blocked")
    @patch("apps.accounts.profiles.views.check_against_blocked_faces", return_value=(True, object(), 0.1))
    @patch("apps.accounts.profiles.views.extract_embedding", return_value=[0.1])
    def test_face_verification_blocked_face_is_not_retryable(self, _embedding, _blocked, _register):
        profile = self.profile()
        ProfilePhoto.objects.create(profile=profile, image=image_file(), order=1, is_main=True)
        response = self.client.post("/api/v1/accounts/face-verify/", {"image": image_file()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data["verified"])
        self.assertFalse(response.data["retryable"])

    @patch("apps.core.utils.face.extract_embedding", return_value=[0.1])
    @patch("apps.core.utils.face.DEEPFACE_AVAILABLE", True)
    @patch("apps.core.utils.face.DeepFace")
    def test_profile_photo_face_detection_does_not_require_liveness(self, deepface, _available, _embedding):
        deepface.extract_faces.return_value = [{"face": object()}]
        is_valid, _, _ = verify_profile_photo(image_file())
        self.assertTrue(is_valid)
        self.assertFalse(deepface.extract_faces.call_args.kwargs["anti_spoofing"])
