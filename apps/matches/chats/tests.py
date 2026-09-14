import uuid

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.profiles.models import (
    CandidateRole,
    GenderType,
    Profile,
    ProfilePhoto,
)
from apps.accounts.users.models import AuthProvider, Role, User
from apps.matches.chats.models import MESSAGE_CONTENT_MAX_LENGTH, ChatRoom, Message
from apps.matches.match_requests.models import MatchRequest, MatchRequestStatus

INMEMORY_CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
}


def _make_user_with_profile(phone, gender, candidate_type):
    """Test uchun foydalanuvchi + anketa yaratadi."""
    role = Role.objects.filter(is_default=True).first()
    user = User.objects.create(
        phone_number=phone, auth_provider=AuthProvider.PHONE, role=role
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


class ChatsTestCase(TestCase):
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
            first_name="User1",
            last_name="Test",
            gender=GenderType.MALE,
            candidate_type=CandidateRole.GROOM,
            birth_date="1995-01-01",
            height=175,
        )

        self.user2 = User.objects.create(
            phone_number="+998902222222",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.profile2 = Profile.objects.create(
            user=self.user2,
            first_name="User2",
            last_name="Test",
            gender=GenderType.FEMALE,
            candidate_type=CandidateRole.BRIDE,
            birth_date="1997-01-01",
            height=165,
        )

        self.match_req = MatchRequest.objects.create(
            from_profile=self.profile1,
            to_profile=self.profile2,
            status=MatchRequestStatus.ACCEPTED,
        )
        self.chat_room = ChatRoom.objects.create(match_request=self.match_req)

    def _create_message(self, sender, content="Asl matn"):
        """Test uchun berilgan foydalanuvchi nomidan xabar yaratadi."""
        return Message.objects.create(
            chat_room=self.chat_room, sender=sender, content=content
        )

    # --- ChatRoom ---

    def test_list_chat_rooms_success(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/v1/matches/chat-rooms/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_chat_rooms_unauthenticated(self):
        response = self.client.get("/api/v1/matches/chat-rooms/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_chat_rooms_returns_partner_name_and_main_photo(self):
        """`partner_info` — so'rov yuborayotgan foydalanuvchiga ko'ra suhbatdoshning
        ismi va faqat asosiy (`is_main=True`) rasmi qaytishini tekshiradi."""
        main_photo = ProfilePhoto.objects.create(
            profile=self.profile2,
            image=SimpleUploadedFile(
                "main.jpg", b"fake-image-bytes", content_type="image/jpeg"
            ),
            order=1,
            is_main=True,
        )
        ProfilePhoto.objects.create(
            profile=self.profile2,
            image=SimpleUploadedFile(
                "other.jpg", b"fake-image-bytes", content_type="image/jpeg"
            ),
            order=2,
            is_main=False,
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/v1/matches/chat-rooms/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        room_data = response.data["results"][0]
        partner = room_data["partner_info"]
        self.assertEqual(partner["full_name"], "User2 Test")
        self.assertIn(main_photo.image.name.rsplit("/", 1)[-1], partner["main_photo"])

    def test_create_chat_room_not_allowed(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            "/api/v1/matches/chat-rooms/",
            {"match_request": str(self.match_req.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_chat_room_by_participant_success(self):
        self._create_message(self.user1)
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(
            f"/api/v1/matches/chat-rooms/{self.chat_room.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.chat_room.refresh_from_db()
        self.assertFalse(self.chat_room.is_active)
        self.assertFalse(
            Message.objects.active().filter(chat_room=self.chat_room).exists()
        )

    def test_delete_chat_room_by_staff_success(self):
        staff_user = User.objects.create(
            phone_number="+998903333333",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_authenticate(user=staff_user)
        response = self.client.delete(
            f"/api/v1/matches/chat-rooms/{self.chat_room.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.chat_room.refresh_from_db()
        self.assertFalse(self.chat_room.is_active)

    def test_delete_chat_room_by_non_participant_not_found(self):
        outsider = _make_user_with_profile(
            "+998904444444", GenderType.MALE, CandidateRole.GROOM
        )
        self.client.force_authenticate(user=outsider)
        response = self.client.delete(
            f"/api/v1/matches/chat-rooms/{self.chat_room.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.chat_room.refresh_from_db()
        self.assertTrue(self.chat_room.is_active)

    def test_delete_chat_room_unauthenticated(self):
        response = self.client.delete(
            f"/api/v1/matches/chat-rooms/{self.chat_room.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Xabar yuborish ---

    def test_send_chat_message_success(self):
        self.client.force_authenticate(user=self.user1)
        data = {"chat_room": str(self.chat_room.id), "content": "Salom, yaxshimisiz?"}
        response = self.client.post("/api/v1/matches/messages/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Message.objects.filter(
                chat_room=self.chat_room,
                sender=self.user1,
                content="Salom, yaxshimisiz?",
            ).exists()
        )

    def test_send_chat_message_unauthenticated(self):
        data = {"chat_room": str(self.chat_room.id), "content": "Salom"}
        response = self.client.post("/api/v1/matches/messages/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_send_empty_message_invalid_data(self):
        self.client.force_authenticate(user=self.user1)
        data = {"chat_room": str(self.chat_room.id), "content": "   "}
        response = self.client.post("/api/v1/matches/messages/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_too_long_message_invalid_data(self):
        self.client.force_authenticate(user=self.user1)
        data = {
            "chat_room": str(self.chat_room.id),
            "content": "a" * (MESSAGE_CONTENT_MAX_LENGTH + 1),
        }
        response = self.client.post("/api/v1/matches/messages/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_message_with_attachment_success(self):
        self.client.force_authenticate(user=self.user1)
        attachment = SimpleUploadedFile(
            "rasm.txt", b"fayl tarkibi", content_type="text/plain"
        )
        response = self.client.post(
            "/api/v1/matches/messages/",
            {"chat_room": str(self.chat_room.id), "attachment": attachment},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        msg = Message.objects.get(chat_room=self.chat_room, sender=self.user1)
        self.assertTrue(msg.attachment)

    def test_send_message_to_others_chat_room_forbidden(self):
        user3 = User.objects.create(
            phone_number="+998903333333",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.client.force_authenticate(user=user3)
        data = {"chat_room": str(self.chat_room.id), "content": "Begona xabar"}
        response = self.client.post("/api/v1/matches/messages/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Xabarni tahrir / o'chirish egaligi ---

    def test_update_own_message_success(self):
        msg = self._create_message(self.user1)
        self.client.force_authenticate(user=self.user1)
        response = self.client.patch(
            f"/api/v1/matches/messages/{msg.id}/",
            {"content": "Tahrirlangan"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        msg.refresh_from_db()
        self.assertEqual(msg.content, "Tahrirlangan")

    def test_update_others_message_forbidden(self):
        msg = self._create_message(self.user1)
        self.client.force_authenticate(user=self.user2)
        response = self.client.patch(
            f"/api/v1/matches/messages/{msg.id}/",
            {"content": "Buzildi"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        msg.refresh_from_db()
        self.assertEqual(msg.content, "Asl matn")

    def test_delete_others_message_forbidden(self):
        msg = self._create_message(self.user1)
        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(f"/api/v1/matches/messages/{msg.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Message.objects.filter(id=msg.id).exists())

    def test_mark_others_message_read_success(self):
        msg = self._create_message(self.user1)
        self.client.force_authenticate(user=self.user2)
        response = self.client.patch(
            f"/api/v1/matches/messages/{msg.id}/",
            {"is_read": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)

    # --- reply_to (xabarga javob) ---

    def test_reply_to_message_success(self):
        original = self._create_message(self.user2, content="Asl savol")
        self.client.force_authenticate(user=self.user1)
        data = {
            "chat_room": str(self.chat_room.id),
            "content": "Mana javob",
            "reply_to": str(original.id),
        }
        response = self.client.post("/api/v1/matches/messages/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["reply_to_info"]["id"], str(original.id))
        msg = Message.objects.get(id=response.data["id"])
        self.assertEqual(msg.reply_to_id, original.id)

    def test_reply_to_message_from_other_room_invalid_data(self):
        other_room = ChatRoom.objects.create(match_request=self.match_req)
        foreign_msg = Message.objects.create(
            chat_room=other_room, sender=self.user2, content="Boshqa xonadagi xabar"
        )
        self.client.force_authenticate(user=self.user1)
        data = {
            "chat_room": str(self.chat_room.id),
            "content": "Javob",
            "reply_to": str(foreign_msg.id),
        }
        response = self.client.post("/api/v1/matches/messages/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reply_to_nonexistent_message_invalid_data(self):
        self.client.force_authenticate(user=self.user1)
        data = {
            "chat_room": str(self.chat_room.id),
            "content": "Javob",
            "reply_to": str(uuid.uuid4()),
        }
        response = self.client.post("/api/v1/matches/messages/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- mark-read / unread-count ---

    def test_mark_read_success(self):
        self._create_message(self.user2, content="1")
        self._create_message(self.user2, content="2")
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            "/api/v1/matches/messages/mark-read/",
            {"chat_room": str(self.chat_room.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["marked_read"], 2)
        self.assertEqual(
            Message.objects.filter(chat_room=self.chat_room, is_read=False).count(),
            0,
        )

    def test_mark_read_others_room_forbidden(self):
        user3 = User.objects.create(
            phone_number="+998904444444",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.client.force_authenticate(user=user3)
        response = self.client.post(
            "/api/v1/matches/messages/mark-read/",
            {"chat_room": str(self.chat_room.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unread_count_success(self):
        self._create_message(self.user2, content="1")
        self._create_message(self.user2, content="2")
        self._create_message(self.user1, content="o'zimniki")
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/v1/matches/messages/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unread"], 2)

    def test_unread_count_unauthenticated(self):
        response = self.client.get("/api/v1/matches/messages/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- onlayn holat ---

    def test_presence_returns_offline_when_partner_not_connected(self):
        cache.delete(f"presence:conn:{self.user2.id}")
        cache.delete(f"presence:last_seen:{self.user2.id}")
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            f"/api/v1/matches/chat-rooms/{self.chat_room.id}/presence/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], str(self.user2.id))
        self.assertEqual(response.data["status"], "offline")

    def test_presence_reflects_connected_partner(self):
        cache.set(f"presence:conn:{self.user2.id}", 1, timeout=70)
        self.addCleanup(cache.delete, f"presence:conn:{self.user2.id}")
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            f"/api/v1/matches/chat-rooms/{self.chat_room.id}/presence/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "online")

    def test_presence_unauthenticated(self):
        response = self.client.get(
            f"/api/v1/matches/chat-rooms/{self.chat_room.id}/presence/"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_presence_not_found_for_non_participant(self):
        outsider = User.objects.create(
            phone_number="+998905555555",
            auth_provider=AuthProvider.PHONE,
            role=self.role,
        )
        self.client.force_authenticate(user=outsider)
        response = self.client.get(
            f"/api/v1/matches/chat-rooms/{self.chat_room.id}/presence/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_presence_all_lists_partner_status(self):
        cache.delete(f"presence:conn:{self.user2.id}")
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/v1/matches/chat-rooms/presence/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(str(self.user2.id), response.data)
        self.assertEqual(response.data[str(self.user2.id)]["status"], "offline")

    # --- tartiblash ---

    def test_messages_ordered_chronologically(self):
        first = self._create_message(self.user1, content="birinchi")
        second = self._create_message(self.user2, content="ikkinchi")
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(
            f"/api/v1/matches/messages/?chat_room={self.chat_room.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(results[0]["id"], str(first.id))
        self.assertEqual(results[1]["id"], str(second.id))


@override_settings(CHANNEL_LAYERS=INMEMORY_CHANNEL_LAYERS)
class ChatWebSocketTestCase(TransactionTestCase):
    def setUp(self):
        self.user1 = _make_user_with_profile(
            "+998911111111", GenderType.MALE, CandidateRole.GROOM
        )
        self.user2 = _make_user_with_profile(
            "+998912222222", GenderType.FEMALE, CandidateRole.BRIDE
        )
        self.outsider = User.objects.create(
            phone_number="+998913333333",
            auth_provider=AuthProvider.PHONE,
            role=Role.objects.filter(is_default=True).first(),
        )
        match_req = MatchRequest.objects.create(
            from_profile=self.user1.profile,
            to_profile=self.user2.profile,
            status=MatchRequestStatus.ACCEPTED,
        )
        self.room = ChatRoom.objects.create(match_request=match_req)

    def _ticket(self, user):
        ticket = str(uuid.uuid4())
        cache.set(f"ws_ticket_{ticket}", user.id, timeout=60)
        return ticket

    def _connect(self, user):
        from config.asgi import application

        ticket = self._ticket(user)
        return WebsocketCommunicator(
            application, f"/ws/chat/{self.room.id}/?ticket={ticket}"
        )

    def test_participant_connects_and_receives_broadcast(self):
        async def scenario():
            from apps.matches.chats.services import broadcast_new_message

            communicator = self._connect(self.user2)
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            msg = await database_sync_to_async(Message.objects.create)(
                chat_room=self.room, sender=self.user1, content="Salom"
            )
            await database_sync_to_async(broadcast_new_message)(msg)

            event = await communicator.receive_json_from(timeout=3)
            self.assertEqual(event["type"], "message")
            self.assertEqual(event["message"]["content"], "Salom")
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_non_participant_rejected(self):
        async def scenario():
            communicator = self._connect(self.outsider)
            connected, _ = await communicator.connect()
            self.assertFalse(connected)

        async_to_sync(scenario)()

    def test_message_sent_over_websocket_persists_and_broadcasts(self):
        async def scenario():
            comm_a = self._connect(self.user1)
            comm_b = self._connect(self.user2)
            self.assertTrue((await comm_a.connect())[0])
            self.assertTrue((await comm_b.connect())[0])

            await comm_a.send_json_to({"type": "message", "content": "WS orqali salom"})

            event = await comm_b.receive_json_from(timeout=3)
            self.assertEqual(event["type"], "message")
            self.assertEqual(event["message"]["content"], "WS orqali salom")

            exists = await database_sync_to_async(
                Message.objects.filter(
                    chat_room=self.room, sender=self.user1, content="WS orqali salom"
                ).exists
            )()
            self.assertTrue(exists)

            await comm_a.disconnect()
            await comm_b.disconnect()

        async_to_sync(scenario)()

    def test_empty_websocket_message_returns_error(self):
        async def scenario():
            comm = self._connect(self.user1)
            self.assertTrue((await comm.connect())[0])
            await comm.send_json_to({"type": "message", "content": "   "})
            event = await comm.receive_json_from(timeout=3)
            self.assertEqual(event["type"], "error")
            await comm.disconnect()

        async_to_sync(scenario)()

    def test_too_long_websocket_message_returns_error(self):
        async def scenario():
            comm = self._connect(self.user1)
            self.assertTrue((await comm.connect())[0])
            await comm.send_json_to(
                {"type": "message", "content": "a" * (MESSAGE_CONTENT_MAX_LENGTH + 1)}
            )
            event = await comm.receive_json_from(timeout=3)
            self.assertEqual(event["type"], "error")
            await comm.disconnect()

        async_to_sync(scenario)()

    def test_websocket_reply_to_message_success(self):
        async def scenario():
            original = await database_sync_to_async(Message.objects.create)(
                chat_room=self.room, sender=self.user2, content="Asl savol"
            )
            comm_a = self._connect(self.user1)
            comm_b = self._connect(self.user2)
            self.assertTrue((await comm_a.connect())[0])
            self.assertTrue((await comm_b.connect())[0])

            await comm_a.send_json_to(
                {
                    "type": "message",
                    "content": "WS javob",
                    "reply_to": str(original.id),
                }
            )

            event = await comm_b.receive_json_from(timeout=3)
            self.assertEqual(event["type"], "message")
            self.assertEqual(event["message"]["reply_to"]["id"], str(original.id))

            new_msg = await database_sync_to_async(
                lambda: Message.objects.get(id=event["message"]["id"]).reply_to_id
            )()
            self.assertEqual(new_msg, original.id)

            await comm_a.disconnect()
            await comm_b.disconnect()

        async_to_sync(scenario)()

    def test_websocket_reply_to_other_room_returns_error(self):
        async def scenario():
            other_room = await database_sync_to_async(ChatRoom.objects.create)(
                match_request_id=self.room.match_request_id
            )
            foreign_msg = await database_sync_to_async(Message.objects.create)(
                chat_room=other_room, sender=self.user2, content="Boshqa xona"
            )
            comm = self._connect(self.user1)
            self.assertTrue((await comm.connect())[0])

            await comm.send_json_to(
                {
                    "type": "message",
                    "content": "Javob",
                    "reply_to": str(foreign_msg.id),
                }
            )

            event = await comm.receive_json_from(timeout=3)
            self.assertEqual(event["type"], "error")
            await comm.disconnect()

        async_to_sync(scenario)()
