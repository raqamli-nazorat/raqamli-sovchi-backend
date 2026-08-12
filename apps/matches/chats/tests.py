from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.matches.chats.models import ChatRoom, Message
from apps.matches.match_requests.models import MatchRequest, MatchRequestStatus
from apps.accounts.profiles.models import Profile, GenderType, CandidateRole
from apps.accounts.users.models import User, AuthProvider, Role


class ChatsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(name="User", is_default=True)

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
            first_name="User2",
            last_name="Test",
            gender=GenderType.FEMALE,
            candidate_type=CandidateRole.BRIDE,
            birth_year=1997,
            height=165,
        )

        self.match_req = MatchRequest.objects.create(
            from_profile=self.profile1,
            to_profile=self.profile2,
            status=MatchRequestStatus.ACCEPTED,
        )
        self.chat_room = ChatRoom.objects.create(match_request=self.match_req)

    def test_list_chat_rooms(self):
        self.client.force_authenticate(user=self.user1)
        url = "/api/v1/matches/chat-rooms/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_send_chat_message(self):
        self.client.force_authenticate(user=self.user1)
        url = "/api/v1/matches/messages/"
        data = {
            "chat_room": str(self.chat_room.id),
            "content": "Salom, yaxshimisiz?",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        msg_exists = Message.objects.filter(
            chat_room=self.chat_room, sender=self.user1, content="Salom, yaxshimisiz?"
        ).exists()
        self.assertTrue(msg_exists)
