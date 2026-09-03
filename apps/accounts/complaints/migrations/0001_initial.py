import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chats", "0003_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Complaint",
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
                    "reason",
                    models.CharField(
                        choices=[
                            ("abusive_language", "Odobsiz so'z"),
                            ("fake_profile", "Soxta profil"),
                            ("fraud", "Firibgarlik"),
                            ("spam", "Spam va reklama"),
                            ("false_information", "Noto'g'ri ma'lumot"),
                            ("threat", "Haqorat va tahdid"),
                            ("no_serious_intent", "Nikoh niyati yo'q"),
                            ("other", "Boshqa"),
                        ],
                        max_length=50,
                        verbose_name="Shikoyat sababi",
                    ),
                ),
                (
                    "message",
                    models.TextField(
                        blank=True, null=True, verbose_name="Qo'shimcha izoh"
                    ),
                ),
                (
                    "evidence",
                    models.JSONField(blank=True, null=True, verbose_name="Dalillar"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Ko'rib chiqilmoqda"),
                            ("approved", "Tasdiqlandi"),
                            ("rejected", "Bekor qilindi"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="Holati",
                    ),
                ),
                (
                    "admin_note",
                    models.TextField(blank=True, null=True, verbose_name="Admin izohi"),
                ),
                (
                    "resolved_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Ko'rib chiqilgan vaqt"
                    ),
                ),
                (
                    "chat_room",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="complaints",
                        to="chats.chatroom",
                        verbose_name="Chat xonasi",
                    ),
                ),
                (
                    "from_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sent_complaints",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Shikoyat yuboruvchi",
                    ),
                ),
                (
                    "resolved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="resolved_complaints",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Ko'rib chiqqan admin",
                    ),
                ),
                (
                    "to_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="received_complaints",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Shikoyat qilingan foydalanuvchi",
                    ),
                ),
            ],
            options={
                "verbose_name": "Shikoyat",
                "verbose_name_plural": "Shikoyatlar",
                "db_table": "complaints",
                "ordering": ["-created_at"],
            },
        ),
    ]
