from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.users.models import User, UserPledge


class UserPledgeOnboardingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(email="pledge@example.com")
        self.other = User.objects.create(email="other-pledge@example.com")
        self.user.user_permissions.add(Permission.objects.get(codename="add_userpledge"))
        self.client.force_authenticate(self.user)

    def test_pledge_binds_user_and_ip_and_is_idempotent(self):
        response = self.client.post(
            "/api/v1/accounts/pledges/",
            {"user": str(self.other.id), "ip_address": "203.0.113.1", "accepted_terms": True},
            format="json", REMOTE_ADDR="198.51.100.2",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pledge = UserPledge.objects.get()
        self.assertEqual(pledge.user, self.user)
        self.assertEqual(pledge.ip_address, "198.51.100.2")
        response = self.client.post("/api/v1/accounts/pledges/", {"accepted_terms": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserPledge.objects.count(), 1)

    def test_pledge_requires_terms_and_only_lists_own_record(self):
        response = self.client.post("/api/v1/accounts/pledges/", {"accepted_terms": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        UserPledge.objects.create(user=self.other, accepted_terms=True)
        response = self.client.get("/api/v1/accounts/pledges/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)
