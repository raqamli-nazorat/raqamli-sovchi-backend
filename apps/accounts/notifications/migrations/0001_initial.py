import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notifications", to=settings.AUTH_USER_MODEL, verbose_name="Foydalanuvchi")),
                ("title", models.CharField(default="", max_length=255, verbose_name="Sarlavha")),
                ("message", models.TextField(default="", verbose_name="Xabar matni")),
                ("extra_data", models.JSONField(blank=True, null=True, verbose_name="Qo'shimcha ma'lumot")),
                ("is_read", models.BooleanField(default=False, verbose_name="O'qilganmi?")),
            ],
            options={
                "verbose_name": "Xabarnoma",
                "verbose_name_plural": "Xabarnomalar",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="UserDevice",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notification_devices", to=settings.AUTH_USER_MODEL)),
                ("fcm_token", models.TextField(unique=True)),
                ("device_type", models.CharField(choices=[("ios", "iOS"), ("android", "Android"), ("web", "Web")], max_length=50)),
                ("device_id", models.CharField(max_length=255, unique=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
