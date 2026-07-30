
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_remove_telegram_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="auth_provider",
            field=models.CharField(
                choices=[
                    ("google", "Google"),
                    ("phone", "Phone"),
                    ("telegram", "Telegram"),
                ],
                default="phone",
                max_length=20,
                verbose_name="Ro'yxatdan o'tgan usuli",
            ),
        ),
    ]
