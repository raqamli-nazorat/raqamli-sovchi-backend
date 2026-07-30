
import django.db.models.deletion
import uuid
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("locations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProfilePhoto",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True, default=True, verbose_name="Is Active"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        verbose_name="Yaratilgan vaqti",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Yangilangan vaqti"
                    ),
                ),
                (
                    "image",
                    models.ImageField(upload_to="profile_photos/", verbose_name="Rasm"),
                ),
                (
                    "order",
                    models.PositiveSmallIntegerField(default=1, verbose_name="Tartib"),
                ),
                (
                    "is_main",
                    models.BooleanField(default=False, verbose_name="Asosiy rasm"),
                ),
            ],
            options={
                "verbose_name": "Profil rasmi",
                "verbose_name_plural": "Profil rasmlari",
                "db_table": "profile_photos",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="RepresentativeInfo",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True, default=True, verbose_name="Is Active"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        verbose_name="Yaratilgan vaqti",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Yangilangan vaqti"
                    ),
                ),
                (
                    "kinship",
                    models.CharField(
                        choices=[
                            ("father", "Ota"),
                            ("mother", "Ona"),
                            ("uncle_paternal", "Amaki"),
                            ("uncle_maternal", "Tog'a"),
                            ("aunt_paternal", "Amma"),
                            ("aunt_maternal", "Xola"),
                            ("other", "Boshqa qarindosh"),
                        ],
                        max_length=30,
                        verbose_name="Qarindoshlik holati",
                    ),
                ),
                (
                    "candidate_role",
                    models.CharField(
                        choices=[("groom", "Kuyov"), ("bride", "Kelin")],
                        max_length=20,
                        verbose_name="Nomzod turi",
                    ),
                ),
            ],
            options={
                "verbose_name": "Vakil ma'lumoti",
                "verbose_name_plural": "Vakil ma'lumotlari",
                "db_table": "representative_infos",
            },
        ),
        migrations.CreateModel(
            name="Profile",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True, default=True, verbose_name="Is Active"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        verbose_name="Yaratilgan vaqti",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Yangilangan vaqti"
                    ),
                ),
                ("first_name", models.CharField(max_length=100, verbose_name="Ismi")),
                (
                    "last_name",
                    models.CharField(max_length=100, verbose_name="Familiyasi"),
                ),
                (
                    "middle_name",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="Otasining ismi",
                    ),
                ),
                (
                    "birth_year",
                    models.PositiveIntegerField(verbose_name="Tug'ilgan yili"),
                ),
                ("height", models.PositiveIntegerField(verbose_name="Bo'yi (sm)")),
                ("weight", models.PositiveIntegerField(verbose_name="Vazni (kg)")),
                (
                    "health_status",
                    models.CharField(
                        choices=[
                            ("healthy", "Sog'lom"),
                            ("disabled", "Nogironligi bor"),
                        ],
                        default="healthy",
                        max_length=20,
                        verbose_name="Sog'liqlik darajasi",
                    ),
                ),
                (
                    "marital_status",
                    models.CharField(
                        choices=[
                            ("never_married", "Birinchi marta turmush qurmoqchi"),
                            ("divorced", "Ajrashgan"),
                        ],
                        max_length=20,
                        verbose_name="Oilaviy holati",
                    ),
                ),
                (
                    "bio",
                    models.TextField(
                        blank=True, null=True, verbose_name="O'zi haqida izoh matn"
                    ),
                ),
                (
                    "voice_intro",
                    models.FileField(
                        blank=True,
                        null=True,
                        upload_to="voice_intros/",
                        verbose_name="Anonim ovozli xabar (Audio)",
                    ),
                ),
                (
                    "latitude",
                    models.DecimalField(
                        blank=True,
                        decimal_places=6,
                        max_digits=9,
                        null=True,
                        verbose_name="Kenglik (Latitude)",
                    ),
                ),
                (
                    "longitude",
                    models.DecimalField(
                        blank=True,
                        decimal_places=6,
                        max_digits=9,
                        null=True,
                        verbose_name="Uzunlik (Longitude)",
                    ),
                ),
                (
                    "blur_photos",
                    models.BooleanField(
                        default=True, verbose_name="Rasmlarni xiralashtirish (Blur)"
                    ),
                ),
                (
                    "district",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="profiles",
                        to="locations.district",
                        verbose_name="Tuman",
                    ),
                ),
                (
                    "region",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="profiles",
                        to="locations.region",
                        verbose_name="Viloyat",
                    ),
                ),
            ],
            options={
                "verbose_name": "Profil Anketa",
                "verbose_name_plural": "Profil Anketalari",
                "db_table": "profiles",
            },
        ),
    ]
