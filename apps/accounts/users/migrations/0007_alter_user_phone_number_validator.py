# Generated manually for phone_number validator

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_remove_user_groups"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="phone_number",
            field=models.CharField(
                db_index=True,
                max_length=20,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Telefon raqami noto'g'ri formatda kiritildi. Kutilgan format: '+998901234567'. Uzunligi aynan 13 ta belgi bo'lishi shart.",
                        regex="^\\+998\\d{9}$",
                    )
                ],
                verbose_name="Telefon raqam",
            ),
        ),
    ]
