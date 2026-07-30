
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_remove_user_pin_code"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="role",
        ),
        migrations.AlterField(
            model_name="user",
            name="groups",
            field=models.ManyToManyField(
                blank=True,
                help_text="Ushbu foydalanuvchi tegishli bo'lgan guruhlar.",
                related_name="custom_user_groups",
                related_query_name="custom_user",
                to="auth.group",
                verbose_name="Guruhlar",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Ushbu foydalanuvchi uchun maxsus ruxsatlar.",
                related_name="custom_user_permissions",
                related_query_name="custom_user_perm",
                to="auth.permission",
                verbose_name="Foydalanuvchi ruxsatlari",
            ),
        ),
    ]
