
import django.db.models.deletion
import uuid
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Region",
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
                ("name", models.CharField(max_length=255, verbose_name="Nomi")),
                (
                    "code",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="Kodi"
                    ),
                ),
            ],
            options={
                "verbose_name": "Viloyat",
                "verbose_name_plural": "Viloyatlar",
            },
        ),
        migrations.CreateModel(
            name="District",
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
                ("name", models.CharField(max_length=255, verbose_name="Nomi")),
                (
                    "code",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="Kodi"
                    ),
                ),
                (
                    "region",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="districts",
                        to="locations.region",
                        verbose_name="Viloyati",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tuman",
                "verbose_name_plural": "Tumanlar",
            },
        ),
    ]
