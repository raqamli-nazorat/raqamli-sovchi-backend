import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("profiles", "0001_initial"),
        ("questionnaire", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MatchRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("from_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_match_requests", to="profiles.profile", verbose_name="Yuboruvchi profil")),
                ("to_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="received_match_requests", to="profiles.profile", verbose_name="Qabul qiluvchi profil")),
                ("status", models.CharField(
                    choices=[("pending", "Kutilmoqda"), ("forwarded_to_representative", "Vakilga yo'naltirildi"), ("accepted", "Qabul qilindi"), ("rejected", "Rad etildi")],
                    default="pending", max_length=35, verbose_name="Holati",
                )),
                ("visibility_scope", models.CharField(
                    choices=[("only_this_user", "Faqat shu odamga ochish"), ("forward_to_representative", "Vakilim hal qilsin")],
                    default="only_this_user", max_length=30, verbose_name="Kimga ochiladi",
                )),
                ("question", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="match_requests", to="questionnaire.question", verbose_name="Savol")),
                ("note", models.TextField(blank=True, null=True, verbose_name="Izoh / O'zi haqida xabar")),
            ],
            options={
                "verbose_name": "Moslik so'rovi",
                "verbose_name_plural": "Moslik so'rovlari",
                "db_table": "match_requests",
            },
        ),
    ]
