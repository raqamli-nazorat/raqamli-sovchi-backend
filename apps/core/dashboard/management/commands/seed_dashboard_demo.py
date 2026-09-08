"""Boshqaruv paneli koʻrsatkichlarini "jonli" koʻrsatish uchun test maʼlumotini tayyorlaydi.

Faqat test userlar (`+99890000` prefiksi) ustida ishlaydi — boshqa yozuvlarga tegmaydi.
Amallar:
  * user / profil / anketa javoblari yaratilgan sanalarini oxirgi N kunga yoyadi
    (oxiriga borgan sari koʻp — oʻsuvchi trend);
  * kuyov↔kelin oʻrtasida MatchRequest (turli status, turli sana) yaratadi;
  * qabul qilingan mosliklarga ChatRoom + Message qoʻshadi (bir qismida oxirgi
    xabar 24 soat ichida — ular "faol suhbat" hisoblanadi);
  * bir nechta Complaint (koʻp qismi "koʻrilmoqda") yaratadi.

Idempotent emas — har ishga tushirishda yangi moslik/suhbat/shikoyat qoʻshiladi.
`--refresh` esa yangi yozuv qoʻshmaydi: faqat mavjud demo suhbat/shikoyat sanasini
hozirgi vaqtga yaqinlashtiradi (demo maʼlumot "eskirganda" `active_chats` /
`complaints_open` koʻrsatkichlarini qayta "jonli" qilish uchun).

Ishlatish:
    python manage.py seed_dashboard_demo
    python manage.py seed_dashboard_demo --days 14
    python manage.py seed_dashboard_demo --refresh   # sanalarni hozirgi vaqtga yaqinlashtiradi
    python manage.py seed_dashboard_demo --clear     # demo maʼlumotni oʻchiradi
"""

import random
from datetime import timedelta

from auditlog.context import disable_auditlog
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.complaints.models import (
    Complaint,
    ComplaintReason,
    ComplaintStatus,
)
from apps.accounts.profiles.management.commands._seed_common import TEST_PHONE_PREFIX
from apps.accounts.profiles.models import CandidateRole, Profile
from apps.accounts.questionnaire.models import UserAnswer
from apps.accounts.users.models import User
from apps.matches.chats.models import ChatRoom, Message
from apps.matches.match_requests.models import MatchRequest, MatchRequestStatus


def _test_users_qs():
    """Test userlar (telefon prefiksi boʻyicha) queryseti."""
    return User.objects.filter(phone_number__startswith=TEST_PHONE_PREFIX)


class Command(BaseCommand):
    help = (
        "Boshqaruv paneli koʻrsatkichlari uchun test moslik/suhbat/shikoyat "
        "maʼlumotini yaratadi (faqat +99890000 prefiksli userlar ustida)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=14, help="Sana yoyish oynasi (kun)."
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Demo maʼlumotni oʻchiradi va sanalarni hozirgi vaqtga qaytaradi.",
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help=(
                "Yangi yozuv qoʻshmaydi — mavjud demo suhbat/shikoyat sanasini "
                "hozirgi vaqtga yaqinlashtiradi (koʻrsatkichlar 'eskirganda')."
            ),
        )

    def handle(self, *args, **options):
        user_ids = list(_test_users_qs().values_list("id", flat=True))
        if not user_ids:
            self.stdout.write(
                self.style.ERROR(
                    "Test user topilmadi. Avval: python manage.py seed_test_candidates"
                )
            )
            return

        with disable_auditlog(), transaction.atomic():
            if options["clear"]:
                self._clear(user_ids)
            elif options["refresh"]:
                self._refresh_recency(user_ids)
            else:
                self._spread_dates(user_ids, options["days"])
                self._make_matches(options["days"])
                self._make_complaints()

        self._bust_dashboard_cache()
        self.stdout.write(self.style.SUCCESS("Tayyor."))

    @staticmethod
    def _bust_dashboard_cache():
        """Boshqaruv paneli / sidebar keshini tozalaydi — natija darhol koʻrinsin."""
        try:
            cache.delete_pattern("dashboard:*")
        except AttributeError:
            # Redis boʻlmagan backend uchun: maʼlum kalitlarni qoʻlda oʻchirish
            cache.delete("dashboard:sidebar")
            cache.delete_many([f"dashboard:summary:{d}" for d in range(1, 91)])

    # --- Tozalash ---

    def _clear(self, user_ids):
        """Test userlarning moslik/suhbat/shikoyatlarini oʻchiradi, sanalarni tiklaydi."""
        from apps.accounts.notifications.models import Notification

        now = timezone.now()
        # MatchRequest oʻchishi ChatRoom + Message ni cascade bilan olib ketadi.
        MatchRequest.objects.filter(from_profile__user_id__in=user_ids).hard_delete()
        Complaint.objects.filter(from_user_id__in=user_ids).hard_delete()
        Notification.objects.filter(user_id__in=user_ids).hard_delete()

        _test_users_qs().update(created_at=now)
        Profile.objects.filter(user_id__in=user_ids).update(created_at=now)
        UserAnswer.objects.filter(profile__user_id__in=user_ids).update(created_at=now)
        self.stdout.write(
            "Demo maʼlumot oʻchirildi, sanalar hozirgi vaqtga qaytarildi."
        )

    # --- Sanalarni yangilash (eskirgan demo uchun) ---

    def _refresh_recency(self, user_ids):
        """Mavjud demo suhbat/shikoyat sanasini hozirgi vaqtga yaqinlashtiradi.

        Yangi yozuv qoʻshilmaydi. Suhbatlarning taxminan yarmida oxirgi xabar
        oxirgi 20 soat ichiga koʻchiriladi — ular yana "faol suhbat" sifatida
        sanaladi; barcha ochiq shikoyatlar ham bugungi kunga tortiladi.
        """
        now = timezone.now()
        rooms = list(
            ChatRoom.objects.filter(
                is_active=True,
                match_request__from_profile__user_id__in=user_ids,
            ).order_by("id")
        )
        refreshed = 0
        for idx, room in enumerate(rooms):
            if idx % 2:  # yarmi eski (nofaol) qoladi
                continue
            last = (
                Message.objects.filter(chat_room=room, is_active=True)
                .order_by("-created_at")
                .first()
            )
            if last is None:
                continue
            Message.objects.filter(id=last.id).update(
                created_at=now - timedelta(hours=random.randint(1, 20))
            )
            refreshed += 1

        open_ids = list(
            Complaint.objects.filter(
                from_user_id__in=user_ids, status=ComplaintStatus.PENDING
            ).values_list("id", flat=True)
        )
        for complaint_id in open_ids:
            Complaint.objects.filter(id=complaint_id).update(
                created_at=now - timedelta(hours=random.randint(1, 20))
            )

        self.stdout.write(
            f"{refreshed} ta suhbat 'faol' holatga, "
            f"{len(open_ids)} ta ochiq shikoyat bugunga yangilandi."
        )

    # --- Sanalarni yoyish ---

    def _spread_dates(self, user_ids, days):
        """User/profil/javob `created_at` ni oxirgi `days` kunga oʻsuvchi trend bilan yoyadi."""
        now = timezone.now()
        users = list(_test_users_qs().order_by("id"))
        buckets = self._weighted_buckets(len(users), days)

        cursor = 0
        for day_offset, n in enumerate(buckets):
            ids = [u.id for u in users[cursor : cursor + n]]
            cursor += n
            if not ids:
                continue
            ts = now - timedelta(
                days=days - 1 - day_offset, hours=random.randint(0, 20)
            )
            _test_users_qs().filter(id__in=ids).update(created_at=ts)
            Profile.objects.filter(user_id__in=ids).update(created_at=ts)
            UserAnswer.objects.filter(profile__user_id__in=ids).update(created_at=ts)
        self.stdout.write(f"{len(users)} ta test user sanasi {days} kunga yoyildi.")

    @staticmethod
    def _weighted_buckets(total, days):
        """`total` ni `days` kunga (i+1) vazn bilan taqsimlaydi (oxiriga borgan sari koʻp)."""
        weights = [i + 1 for i in range(days)]
        wsum = sum(weights)
        buckets = [round(total * w / wsum) for w in weights]
        buckets[-1] += total - sum(buckets)  # yaxlitlash qoldigʻi oxirgi kunga
        return buckets

    # --- Mosliklar va suhbatlar ---

    def _make_matches(self, days):
        """Kuyov→kelin MatchRequest larini turli status va sana bilan yaratadi."""
        grooms = self._role_profiles(CandidateRole.GROOM)
        brides = self._role_profiles(CandidateRole.BRIDE)
        if not grooms or not brides:
            self.stdout.write(
                "Kuyov/kelin profillari yetarli emas — moslik oʻtkazib yuborildi."
            )
            return

        now = timezone.now()
        pairs = min(len(grooms), len(brides))
        statuses = (
            [MatchRequestStatus.ACCEPTED] * round(pairs * 0.55)
            + [MatchRequestStatus.PENDING] * round(pairs * 0.30)
            + [MatchRequestStatus.REJECTED] * pairs
        )[:pairs]
        random.shuffle(statuses)

        accepted = []
        for i in range(pairs):
            created = now - timedelta(
                days=random.randint(0, days - 1), hours=random.randint(0, 22)
            )
            mr = MatchRequest.objects.create(
                from_profile=grooms[i], to_profile=brides[i], status=statuses[i]
            )
            MatchRequest.objects.filter(id=mr.id).update(created_at=created)
            if statuses[i] == MatchRequestStatus.ACCEPTED:
                accepted.append((mr, created))

        self._make_chats(accepted)
        self.stdout.write(
            f"{pairs} ta moslik ({len(accepted)} qabul qilingan) yaratildi."
        )

    @staticmethod
    def _role_profiles(role):
        """Berilgan roldagi test profillari (id boʻyicha tartiblangan)."""
        return list(
            Profile.objects.filter(
                user__phone_number__startswith=TEST_PHONE_PREFIX, candidate_type=role
            ).order_by("id")
        )

    def _make_chats(self, accepted):
        """Qabul qilingan mosliklarga suhbat va xabarlar qoʻshadi.

        Roʻyxatning taxminan yarmida oxirgi xabar 24 soat ichida — bu suhbatlar
        boshqaruv panelida "faol suhbat" sifatida sanaladi.
        """
        now = timezone.now()
        for idx, (mr, created) in enumerate(accepted):
            room = ChatRoom.objects.create(match_request=mr)
            ChatRoom.objects.filter(id=room.id).update(created_at=created)

            recent = idx % 2 == 0
            last_ts = (
                now - timedelta(hours=random.randint(1, 20))
                if recent
                else now - timedelta(days=random.randint(3, 10))
            )
            participants = [mr.from_profile.user, mr.to_profile.user]
            msgs = [
                Message.objects.create(
                    chat_room=room,
                    sender=participants[j % 2],
                    content="Assalomu alaykum, yaqinroq tanishsak.",
                )
                for j in range(random.randint(2, 5))
            ]
            for k, msg in enumerate(reversed(msgs)):
                Message.objects.filter(id=msg.id).update(
                    created_at=last_ts - timedelta(hours=k)
                )

    # --- Shikoyatlar ---

    def _make_complaints(self):
        """Bir nechta shikoyat yaratadi (4 tasi "koʻrilmoqda", 2 tasi "bekor qilingan")."""
        users = list(_test_users_qs().order_by("id")[:12])
        if len(users) < 2:
            return

        now = timezone.now()
        reasons = [
            ComplaintReason.SPAM,
            ComplaintReason.FAKE_PROFILE,
            ComplaintReason.ABUSIVE_LANGUAGE,
            ComplaintReason.FALSE_INFORMATION,
        ]
        for i in range(6):
            status = ComplaintStatus.PENDING if i < 4 else ComplaintStatus.REJECTED
            complaint = Complaint.objects.create(
                from_user=users[i],
                to_user=users[(i + 1) % len(users)],
                reason=random.choice(reasons),
                message="Test shikoyat matni.",
                status=status,
            )
            Complaint.objects.filter(id=complaint.id).update(
                created_at=now - timedelta(days=random.randint(0, 3))
            )
        self.stdout.write("6 ta shikoyat yaratildi (4 tasi koʻrilmoqda).")
