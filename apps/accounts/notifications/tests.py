from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.users.models import User, AuthProvider, Role
from apps.accounts.notifications.models import Notification, UserDevice
from apps.accounts.notifications.tasks import (
    send_push_notification_task,
    send_single_notification_task,
    NotificationPayload,
)


class NotificationsApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(name="User Role", is_default=True)
        self.user = User.objects.create(
            phone_number="+998901234567",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.client.force_authenticate(user=self.user)

    def test_websocket_ticket_creation(self):
        url = "/api/v1/accounts/notifications/tickets/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("ticket", response.data)
        self.assertEqual(response.data["expires_in"], 60)

        ticket = response.data["ticket"]
        cached_user_id = cache.get(f"ws_ticket_{ticket}")
        self.assertEqual(cached_user_id, self.user.id)

    def test_device_register_and_restore_active(self):
        url = "/api/v1/accounts/notifications/devices/register/"
        data = {
            "fcm_token": "token_abc_123",
            "device_type": "android",
            "device_id": "device_unique_123",
        }
        # 1. Register device
        res = self.client.post(url, data=data, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "created")

        device = UserDevice.objects.get(device_id="device_unique_123")
        self.assertEqual(device.user, self.user)
        self.assertTrue(device.is_active)

        # 2. Deactivate device manually
        device.is_active = False
        device.save()

        # 3. Register again - should restore is_active=True
        res2 = self.client.post(url, data=data, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["status"], "updated")

        device.refresh_from_db()
        self.assertTrue(device.is_active)

    def test_device_unregister_current(self):
        # Create active device
        device = UserDevice.objects.create(
            user=self.user,
            fcm_token="token_unregister_test",
            device_type="ios",
            device_id="device_to_unregister",
            is_active=True,
        )
        url = "/api/v1/accounts/notifications/devices/current/"
        res = self.client.delete(url, data={"device_id": "device_to_unregister"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        device.refresh_from_db()
        self.assertFalse(device.is_active)


class PushNotificationTaskTestCase(TestCase):
    def setUp(self):
        self.role = Role.objects.create(name="User Role", is_default=True)
        self.user = User.objects.create(
            phone_number="+998909876543",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.active_device = UserDevice.objects.create(
            user=self.user,
            fcm_token="active_token_1",
            device_type="android",
            device_id="active_dev_1",
            is_active=True,
        )
        self.inactive_device = UserDevice.objects.create(
            user=self.user,
            fcm_token="inactive_token_2",
            device_type="android",
            device_id="inactive_dev_2",
            is_active=False,
        )

    @patch("firebase_admin.messaging.send_each_for_multicast")
    def test_send_push_notification_task_filters_active_devices_only(self, mock_send):
        mock_response = MagicMock()
        mock_response.success_count = 1
        mock_response.failure_count = 0
        mock_response.responses = [MagicMock(success=True)]
        mock_send.return_value = mock_response

        res = send_push_notification_task(
            user_id=str(self.user.id),
            notification_id="test_notif_123",
            title="Test Title",
            message="Test Body",
            extra_data={"key": "val"},
        )

        mock_send.assert_called_once()
        multicast_msg = mock_send.call_args[0][0]
        self.assertEqual(multicast_msg.tokens, ["active_token_1"])
        self.assertIn("FCM: 1 muvaffaqiyatli", res)

    @patch("firebase_admin.messaging.send_each_for_multicast")
    def test_invalid_token_cleanup_deactivates_device(self, mock_send):
        mock_resp_item = MagicMock(success=False)
        from firebase_admin import messaging
        mock_resp_item.exception = messaging.UnregisteredError("Unregistered")

        mock_response = MagicMock()
        mock_response.success_count = 0
        mock_response.failure_count = 1
        mock_response.responses = [mock_resp_item]
        mock_send.return_value = mock_response

        send_push_notification_task(
            user_id=str(self.user.id),
            notification_id="test_notif_456",
            title="Test",
            message="Test",
        )

        self.active_device.refresh_from_db()
        self.assertFalse(self.active_device.is_active)

    def test_notification_payload_dataclass(self):
        payload_dict = {
            "user_id": str(self.user.id),
            "notification_id": "notif_uuid_789",
            "title": "Salom",
            "message": "Xabar matni",
            "extra_data": {"type": "match_request"},
        }
        p = NotificationPayload.from_dict(payload_dict)
        self.assertEqual(p.user_id, str(self.user.id))
        self.assertEqual(p.notification_id, "notif_uuid_789")
        self.assertEqual(p.schema_version, "1")
