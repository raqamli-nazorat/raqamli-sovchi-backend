import uuid
from unittest.mock import MagicMock, patch

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.notifications.models import UserDevice
from apps.accounts.notifications.presence import get_presence, mark_offline, mark_online
from apps.accounts.notifications.tasks import (
    NotificationPayload,
    send_push_notification_task,
)
from apps.accounts.profiles.models import CandidateRole, GenderType, Profile
from apps.accounts.users.models import AuthProvider, Role, User
from apps.matches.chats.models import ChatRoom
from apps.matches.match_requests.models import MatchRequest, MatchRequestStatus

INMEMORY_CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
}


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
        res = self.client.delete(
            url, data={"device_id": "device_to_unregister"}, format="json"
        )
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


class PresenceHelperTestCase(TestCase):
    def setUp(self):
        self.role = Role.objects.create(name="User Role", is_default=True)
        self.user = User.objects.create(
            phone_number="+998900000009",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        cache.delete(f"presence:conn:{self.user.id}")
        cache.delete(f"presence:last_seen:{self.user.id}")

    def test_mark_online_then_offline_updates_presence(self):
        became_online = mark_online(self.user.id)
        self.assertTrue(became_online)
        self.assertEqual(get_presence(self.user.id)["status"], "online")

        became_offline, last_seen = mark_offline(self.user.id)
        self.assertTrue(became_offline)
        self.assertIsNotNone(last_seen)

        state = get_presence(self.user.id)
        self.assertEqual(state["status"], "offline")
        self.assertEqual(state["last_seen"], last_seen)

    def test_second_connection_does_not_re_trigger_online(self):
        self.assertTrue(mark_online(self.user.id))
        self.assertFalse(mark_online(self.user.id))

        became_offline, _ = mark_offline(self.user.id)
        self.assertFalse(became_offline)
        self.assertEqual(get_presence(self.user.id)["status"], "online")


@override_settings(CHANNEL_LAYERS=INMEMORY_CHANNEL_LAYERS)
class NotificationPresenceWebSocketTestCase(TransactionTestCase):
    def setUp(self):
        self.role = Role.objects.filter(is_default=True).first()
        self.user1 = self._make_user(
            "+998921111111", GenderType.MALE, CandidateRole.GROOM
        )
        self.user2 = self._make_user(
            "+998922222222", GenderType.FEMALE, CandidateRole.BRIDE
        )
        match_req = MatchRequest.objects.create(
            from_profile=self.user1.profile,
            to_profile=self.user2.profile,
            status=MatchRequestStatus.ACCEPTED,
        )
        ChatRoom.objects.create(match_request=match_req)
        for u in (self.user1, self.user2):
            cache.delete(f"presence:conn:{u.id}")

    def _make_user(self, phone, gender, candidate_type):
        user = User.objects.create(
            phone_number=phone, auth_provider=AuthProvider.PHONE, role=self.role
        )
        Profile.objects.create(
            user=user,
            first_name=phone[-4:],
            last_name="Test",
            gender=gender,
            candidate_type=candidate_type,
            birth_date="1995-01-01",
            height=175,
        )
        return user

    def _connect(self, user):
        from config.asgi import application

        ticket = str(uuid.uuid4())
        cache.set(f"ws_ticket_{ticket}", user.id, timeout=60)
        return WebsocketCommunicator(application, f"/ws/notifications/?ticket={ticket}")

    def test_partner_receives_online_and_offline_events(self):
        async def scenario():
            watcher = self._connect(self.user2)
            self.assertTrue((await watcher.connect())[0])

            mover = self._connect(self.user1)
            self.assertTrue((await mover.connect())[0])

            event = await watcher.receive_json_from(timeout=3)
            self.assertEqual(event["type"], "presence")
            self.assertEqual(event["user"], str(self.user1.id))
            self.assertEqual(event["status"], "online")

            await mover.disconnect()

            event = await watcher.receive_json_from(timeout=3)
            self.assertEqual(event["status"], "offline")
            self.assertIsNotNone(event["last_seen"])

            await watcher.disconnect()

        async_to_sync(scenario)()

    def test_ping_receives_pong(self):
        async def scenario():
            comm = self._connect(self.user1)
            self.assertTrue((await comm.connect())[0])
            await comm.send_json_to({"type": "ping"})
            event = await comm.receive_json_from(timeout=3)
            self.assertEqual(event["type"], "pong")
            await comm.disconnect()

        async_to_sync(scenario)()
