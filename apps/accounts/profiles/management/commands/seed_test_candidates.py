"""Farg'ona viloyati bo'yicha to'liq ma'lumotli test nomzod va vakillar yaratadi.

Har bir yaratilgan yozuv: User + UserPledge + Profile + 1-3 ProfilePhoto +
so'rovnoma javoblari (UserAnswer), vakillar uchun qo'shimcha RepresentativeInfo.
Barcha profillar `region = Farg'ona viloyati` va Farg'ona tumanlaridan biriga tegishli.

Tasdiqlashsiz, bitta buyruq bilan ishlaydi. Idempotent: har ishga tushirishda avval
mavjud test userlar (`+99890000` prefiksi) to'liq o'chirilib, yangidan yaratiladi.

Ishlatish:
    python manage.py seed_test_candidates            # 100 ta
    python manage.py seed_test_candidates --count 50
"""

import io
import random
from datetime import date, timedelta

from auditlog.context import disable_auditlog
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageDraw

from apps.accounts.profiles.models import (
    CandidateRole,
    GenderType,
    Profile,
    ProfilePhoto,
    RepresentativeInfo,
)
from apps.accounts.questionnaire.models import Question, UserAnswer
from apps.accounts.questionnaire.services import get_effective_candidate_role
from apps.accounts.users.models import AuthProvider, Role, User, UserPledge
from apps.core.references.models import (
    EducationLevel,
    HealthStatus,
    Kinship,
    MaritalStatus,
    Nationality,
    Profession,
)

from ._seed_common import REGION_NAME, TEST_PHONE_PREFIX, delete_test_data

# --- Statik generatsiya poollari (o'zbekcha, tashqi kutubxonasiz) ---

MALE_NAMES = [
    "Akmal",
    "Bekzod",
    "Doston",
    "Eldor",
    "Farrux",
    "G'ayrat",
    "Hasan",
    "Islom",
    "Jasur",
    "Kamron",
    "Laziz",
    "Muhammadali",
    "Nodir",
    "Otabek",
    "Po'lat",
    "Rustam",
    "Sardor",
    "Temur",
    "Ulug'bek",
    "Sherzod",
    "Xurshid",
    "Sanjar",
    "Zafar",
    "Abror",
    "Bahodir",
    "Diyor",
    "Jamshid",
    "Nurbek",
    "Shohruh",
    "Aziz",
]
FEMALE_NAMES = [
    "Aziza",
    "Barno",
    "Dilnoza",
    "Gulnora",
    "Farida",
    "Gulbahor",
    "Hilola",
    "Iroda",
    "Jamila",
    "Kamola",
    "Laylo",
    "Madina",
    "Nigora",
    "Ozoda",
    "Parvina",
    "Ra'no",
    "Sevara",
    "Shahnoza",
    "Umida",
    "Malika",
    "Xurshida",
    "Yulduz",
    "Zilola",
    "Nozima",
    "Dildora",
    "Feruza",
    "Kamila",
    "Mohira",
    "Nasiba",
    "Sabina",
]
SURNAME_BASES = [
    "Karim",
    "Rahim",
    "Yusup",
    "Tosh",
    "Ergash",
    "Qodir",
    "Nazar",
    "Sobir",
    "Umar",
    "Islom",
    "Xolmat",
    "Rasul",
    "Mahmud",
    "Hakim",
    "Sulton",
    "Toir",
    "G'ani",
    "Mirzo",
    "Odil",
    "Vali",
]
EXPECTATIONS = [
    "Oilaparvar, dinini biladigan, bir-birini hurmat qiladigan juft izlayapman.",
    "Sadoqatli, mas'uliyatli va tinch-totuv hayot qadrini biladigan inson.",
    "Kelajakka umumiy qarashlarimiz mos keladigan, halol va mehnatkash juft.",
    "Bir-birini tushunadigan, oila qadriyatlarini birinchi o'ringa qo'yadigan inson.",
]
BIOS = [
    "Farg'onada tug'ilib o'sganman. Ishimni va oilamni bir xil qadrlayman.",
    "Sokin muhitni, kitob o'qishni va yaqinlar bilan vaqt o'tkazishni yoqtiraman.",
    "Hayotga jiddiy qarayman, mustahkam va samimiy oila qurishni maqsad qilganman.",
    "O'z ustimda ishlayman, sport bilan shug'ullanaman, oilaviy an'analarni hurmat qilaman.",
]
_PALETTE = [
    (91, 124, 250),
    (240, 128, 128),
    (76, 175, 122),
    (255, 167, 82),
    (149, 117, 205),
    (0, 172, 193),
    (236, 100, 168),
    (120, 144, 156),
]


def _weighted(pool, preferred_name, probability):
    """Berilgan ehtimollik bilan `preferred_name` li elementni, aks holda random tanlaydi."""
    preferred = next((item for item in pool if item.name == preferred_name), None)
    if preferred and random.random() < probability:
        return preferred
    return random.choice(pool)


def _generate_image(label, color):
    """Placeholder profil rasmi (JPEG bytes) yaratadi — ustiga bosh harflar yoziladi."""
    img = Image.new("RGB", (600, 600), color)
    draw = ImageDraw.Draw(img)
    draw.text((260, 270), label, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return buf.getvalue()


def _build_answers(profile):
    """Profilning amaldagi roli (kuyov/kelin) bo'yicha barcha savollarga javob yozadi.

    Har profilga tasodifiy "arxetip" beriladi va javoblar shu atrofda ozgina
    shovqin bilan tanlanadi — natijada moslik ballari 100% emas, real taqsimlanadi.
    """
    role = get_effective_candidate_role(profile)
    questions = Question.objects.filter(target_gender=role).prefetch_related("options")
    archetype = random.randint(0, 3)

    answers = []
    for question in questions:
        options = sorted(question.options.all(), key=lambda opt: opt.option_letter)
        if not options:
            continue
        idx = archetype + random.choice([-1, 0, 0, 1])
        idx = max(0, min(idx, len(options) - 1))
        answers.append(
            UserAnswer(
                profile=profile,
                question=question,
                selected_option=options[idx],
            )
        )
    UserAnswer.objects.bulk_create(answers, ignore_conflicts=True)


class Command(BaseCommand):
    help = (
        "Farg'ona viloyati bo'yicha to'liq ma'lumotli test nomzod va vakillar yaratadi "
        "(User + Pledge + Profile + rasmlar + so'rovnoma javoblari)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Yaratiladigan yozuvlar soni (default 100)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="random.seed (takrorlanuvchanlik uchun)",
        )

    def handle(self, *args, **options):
        if options["count"] < 2:
            raise CommandError("--count kamida 2 bo'lishi kerak.")
        if options["seed"] is not None:
            random.seed(options["seed"])

        # Idempotent: har ishga tushirishda avvalgi test userlar to'liq tozalanadi.
        delete_test_data(self.stdout)

        with disable_auditlog(), transaction.atomic():
            self._seed(options["count"])

    def _seed(self, count):
        """Asosiy generatsiya: nomzodlar, keyin ularга biriktiriladigan vakillar."""
        pools = self._reference_pools()
        districts = self._fergana_districts()

        if not districts:
            raise CommandError(
                f"'{REGION_NAME}' uchun tuman topilmadi. "
                "Avval: python manage.py load_locations"
            )
        if not pools["education"] or not Question.objects.exists():
            raise CommandError(
                "Ma'lumotnoma yoki savollar bazada yo'q. Avval: "
                "python manage.py load_references && python manage.py load_questions"
            )

        role_obj = Role.objects.filter(is_default=True).first()

        n_rep = max(1, round(count * 0.10)) if count >= 10 else 0
        n_rest = count - n_rep
        n_groom = n_rest // 2
        n_bride = n_rest - n_groom

        index = 1
        for _ in range(n_groom):
            self._build_candidate(index, "groom", pools, districts, role_obj)
            index += 1
        for _ in range(n_bride):
            self._build_candidate(index, "bride", pools, districts, role_obj)
            index += 1
        for i in range(n_rep):
            represents = "groom" if i % 2 == 0 else "bride"
            self._build_representative(index, represents, pools, districts, role_obj)
            index += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Tayyor: {n_groom} kuyov, {n_bride} kelin, {n_rep} vakil "
                f"({REGION_NAME}) yaratildi."
            )
        )

    # --- Quyi darajali yordamchilar ---

    def _reference_pools(self):
        """Ma'lumotnoma jadvallarini bir marta xotiraga o'qib, lug'at qaytaradi."""
        return {
            "education": list(EducationLevel.objects.all()),
            "nationality": list(Nationality.objects.all()),
            "profession": list(Profession.objects.all()),
            "marital": list(MaritalStatus.objects.all()),
            "health": list(HealthStatus.objects.all()),
            "kinship": list(Kinship.objects.all()),
        }

    def _fergana_districts(self):
        """Farg'ona viloyatiga tegishli barcha tumanlar ro'yxatini qaytaradi."""
        from apps.core.locations.models import District

        qs = District.objects.filter(region__name=REGION_NAME)
        if not qs.exists():
            qs = District.objects.filter(region__name__icontains="rg'ona")
        return list(qs)

    def _make_user(self, index, role_obj):
        """Parolsiz, tasdiqlangan test user + halollik roziligini (pledge) yaratadi."""
        user = User.objects.create(
            phone_number=f"{TEST_PHONE_PREFIX}{index:04d}",
            auth_provider=AuthProvider.PHONE,
            role=role_obj,
            is_active=True,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        # UserPledge.save() ichida user.is_verified=True bo'ladi.
        UserPledge.objects.create(
            user=user, accepted_terms=True, has_serious_badge=True
        )
        return user

    def _make_profile(self, user, role, gender, pools, districts):
        """Barcha maydonlari to'ldirilgan Profile yaratadi (region — doim Farg'ona)."""
        is_male = gender == GenderType.MALE
        base = random.choice(SURNAME_BASES)
        age = random.randint(20, 40)
        marital = _weighted(pools["marital"], "Turmush qurmagan", 0.8)
        has_kids = marital.name != "Turmush qurmagan" and random.random() < 0.5

        return Profile.objects.create(
            user=user,
            first_name=random.choice(MALE_NAMES if is_male else FEMALE_NAMES),
            last_name=base + ("ev" if is_male else "eva"),
            middle_name=random.choice(MALE_NAMES) + (" o'g'li" if is_male else " qizi"),
            gender=gender,
            candidate_type=(
                role if role in ("groom", "bride") else CandidateRole.REPRESENTATIVE
            ),
            birth_date=date.today()
            - timedelta(days=age * 365 + random.randint(0, 364)),
            height=random.randint(165, 188) if is_male else random.randint(150, 175),
            weight=random.randint(55, 95) if is_male else random.randint(45, 75),
            region=districts[0].region,
            district=random.choice(districts),
            health_status=_weighted(pools["health"], "Sog'lom", 0.9),
            marital_status=marital,
            education_level=random.choice(pools["education"]),
            nationality=_weighted(pools["nationality"], "O'zbek", 0.85),
            profession=random.choice(pools["profession"]),
            has_children=has_kids,
            children_count=random.randint(1, 3) if has_kids else 0,
            expectations=random.choice(EXPECTATIONS),
            bio=random.choice(BIOS),
            # Farg'ona shahri atrofidagi koordinatalar — save() PointField ni to'ldiradi.
            latitude=round(random.uniform(40.28, 40.55), 6),
            longitude=round(random.uniform(71.55, 72.05), 6),
            blur_photos=random.choice([True, False]),
        )

    def _make_photos(self, profile):
        """Profilga 1-3 ta placeholder rasm biriktiradi (birinchisi asosiy)."""
        color = _PALETTE[hash(str(profile.id)) % len(_PALETTE)]
        label = (profile.first_name[:1] + profile.last_name[:1]).upper()
        for order in range(1, random.randint(1, 3) + 1):
            ProfilePhoto.objects.create(
                profile=profile,
                image=ContentFile(
                    _generate_image(label, color), name=f"seed_{profile.id}_{order}.jpg"
                ),
                order=order,
                is_main=(order == 1),
            )

    def _build_candidate(self, index, role, pools, districts, role_obj):
        """Bitta nomzod (kuyov yoki kelin): user + profil + rasmlar + javoblar."""
        gender = GenderType.MALE if role == "groom" else GenderType.FEMALE
        user = self._make_user(index, role_obj)
        profile = self._make_profile(user, role, gender, pools, districts)
        self._make_photos(profile)
        _build_answers(profile)
        return profile

    def _build_representative(self, index, represents, pools, districts, role_obj):
        """Bitta vakil: profil + rasmlar + javoblar + RepresentativeInfo.

        Vakilning jinsi `represents` bilan moslashtiriladi (groom->erkak, bride->ayol),
        chunki "amaldagi rol" 3 joyda alohida hisoblanadi
        (get_effective_candidate_role gender orqali, is_female_candidate,
        filter_profiles_for_user candidate_role orqali) — jins mos bo'lsa uchalasi bir xil natija beradi.
        """
        gender = GenderType.MALE if represents == "groom" else GenderType.FEMALE
        user = self._make_user(index, role_obj)
        profile = self._make_profile(user, "representative", gender, pools, districts)

        target = (
            User.objects.filter(
                phone_number__startswith=TEST_PHONE_PREFIX,
                profile__candidate_type=represents,
                represented_by_infos__isnull=True,
            )
            .order_by("phone_number")
            .first()
        )
        RepresentativeInfo.objects.create(
            profile=profile,
            kinship=random.choice(pools["kinship"]),
            candidate_role=represents,
            candidate_contact=(
                target.phone_number if target else f"{TEST_PHONE_PREFIX}0000"
            ),
            target_candidate=target,
            is_approved=True,
        )
        self._make_photos(profile)
        _build_answers(profile)
        return profile
