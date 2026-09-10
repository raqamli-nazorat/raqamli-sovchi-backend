"""Real-time chatni qo'lda sinash uchun ikkita user + qabul qilingan match + xona tayyorlaydi.

Har user uchun JWT access token, WebSocket ticket va tayyor `ws://` URL chop etadi.
Idempotent: qayta ishga tushirilsa o'sha userlarni qayta ishlatadi.

Ishlatish:
    python manage.py chat_e2e
    python manage.py chat_e2e --ticket-ttl 3600      # ticket 1 soat amal qiladi (sinov uchun)
    python manage.py chat_e2e --host 127.0.0.1:8000
    python manage.py chat_e2e --reset                # avval test userlarni o'chirib, qaytadan
"""

import uuid

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.profiles.models import CandidateRole, GenderType, Profile
from apps.accounts.users.models import AuthProvider, Role, User
from apps.accounts.users.utils import get_tokens_for_user
from apps.matches.chats.models import ChatRoom
from apps.matches.match_requests.models import MatchRequest, MatchRequestStatus

# Test userlar shu ikki raqamda qat'iy — prod raqamlariga tegmaydi
PHONE_A = "+998990000001"
PHONE_B = "+998990000002"


class Command(BaseCommand):
    help = "Real-time chat sinovi uchun 2 user + xona + tokenlar tayyorlaydi"

    def add_arguments(self, parser):
        parser.add_argument("--host", default="127.0.0.1:8000", help="Server host:port")
        parser.add_argument(
            "--ticket-ttl",
            type=int,
            default=60,
            help="WebSocket ticket amal qilish muddati, soniya (sinov uchun kattaroq qo'ying)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Avval mavjud test userlarni (va ularning xonasini) o'chirib tashlaydi",
        )

    def handle(self, *args, **opts):
        host = opts["host"]
        ttl = opts["ticket_ttl"]

        if opts["reset"]:
            User.objects.filter(phone_number__in=[PHONE_A, PHONE_B]).delete()
            self.stdout.write(self.style.WARNING("Eski test userlar o'chirildi."))

        with transaction.atomic():
            user_a, profile_a = self._ensure_user(
                PHONE_A, "Akmal", GenderType.MALE, CandidateRole.GROOM
            )
            user_b, profile_b = self._ensure_user(
                PHONE_B, "Malika", GenderType.FEMALE, CandidateRole.BRIDE
            )

            match_req, _ = MatchRequest.objects.get_or_create(
                from_profile=profile_a,
                to_profile=profile_b,
                defaults={"status": MatchRequestStatus.ACCEPTED},
            )
            if match_req.status != MatchRequestStatus.ACCEPTED:
                match_req.status = MatchRequestStatus.ACCEPTED
                match_req.save(update_fields=["status", "updated_at"])

            room, _ = ChatRoom.objects.get_or_create(match_request=match_req)

        self.stdout.write(self.style.SUCCESS("\n=== CHAT E2E TAYYOR ===\n"))
        self.stdout.write(f"Chat xonasi ID : {room.id}")
        self.stdout.write(f"Match so'rovi  : {match_req.id} ({match_req.status})\n")

        for label, user in (("A", user_a), ("B", user_b)):
            ticket = uuid.uuid4().hex
            cache.set(f"ws_ticket_{ticket}", user.id, timeout=ttl)
            tokens = get_tokens_for_user(user)

            self.stdout.write(self.style.HTTP_INFO(f"\n--- USER {label} ---"))
            self.stdout.write(f"phone      : {user.phone_number}")
            self.stdout.write(f"user_id    : {user.id}")
            self.stdout.write(f"access     : {tokens['access']}")
            self.stdout.write(f"ws ticket  : {ticket}  (amal qiladi: {ttl}s)")
            self.stdout.write(
                self.style.SUCCESS(
                    f"WS URL     : ws://{host}/ws/chat/{room.id}/?ticket={ticket}"
                )
            )

        self.stdout.write(
            self.style.HTTP_INFO("\n--- XABAR YUBORISH (REST -> WS ga tarqaladi) ---")
        )
        self.stdout.write(
            f"curl -X POST http://{host}/api/v1/matches/messages/ \\\n"
            f"  -H 'Authorization: Bearer <USER_A_ACCESS>' \\\n"
            f"  -H 'Content-Type: application/json' \\\n"
            f'  -d \'{{"chat_room":"{room.id}","content":"Salom B!"}}\''
        )
        self.stdout.write(
            self.style.WARNING(
                "\nEslatma: server ASGI da ishlashi shart -> `python manage.py runserver` "
                "(daphne avtomatik) yoki `daphne -b 127.0.0.1 -p 8000 config.asgi:application`. "
                "Redis yoniq bo'lsin. Ticket muddati o'tsa buyruqni qayta ishga tushiring."
            )
        )

    def _ensure_user(self, phone, name, gender, candidate_type):
        """Berilgan raqamda user + anketa yaratadi yoki mavjudini qaytaradi."""
        role = Role.objects.filter(is_default=True).first()
        user, _ = User.objects.get_or_create(
            phone_number=phone,
            defaults={
                "auth_provider": AuthProvider.PHONE,
                "role": role,
                "is_active": True,
            },
        )
        if (
            user.is_blocked
            or not user.is_active
            or user.role_id != getattr(role, "id", None)
        ):
            user.is_blocked = False
            user.is_active = True
            user.role = role
            user.save(update_fields=["is_blocked", "is_active", "role", "updated_at"])

        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                "first_name": name,
                "last_name": "Sinov",
                "gender": gender,
                "candidate_type": candidate_type,
                "birth_date": "1995-01-01",
                "height": 175,
            },
        )
        return user, profile
