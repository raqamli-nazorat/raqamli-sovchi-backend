import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("match_requests", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatRoom",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("match_request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_rooms", to="match_requests.matchrequest", verbose_name="Moslik so'rovi")),
            ],
            options={
                "verbose_name": "Chat xonasi",
                "verbose_name_plural": "Chat xonalari",
                "db_table": "chat_rooms",
            },
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("chat_room", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="chats.chatroom", verbose_name="Chat xonasi")),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_messages", to=settings.AUTH_USER_MODEL, verbose_name="Yuboruvchi")),
                ("content", models.TextField(verbose_name="Xabar matni")),
                ("is_read", models.BooleanField(default=False, verbose_name="O'qilganligi")),
            ],
            options={
                "verbose_name": "Xabar",
                "verbose_name_plural": "Xabarlar",
                "db_table": "messages",
            },
        ),
    ]
