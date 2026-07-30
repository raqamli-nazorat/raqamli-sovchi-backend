from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0004_profile_gender"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="role",
            field=models.CharField(
                blank=True,
                choices=[
                    ("groom", "Kuyov"),
                    ("bride", "Kelin"),
                    ("representative", "Vakil"),
                ],
                max_length=20,
                null=True,
                verbose_name="Roli (Kuyov/Kelin/Vakil)",
            ),
        ),
    ]
