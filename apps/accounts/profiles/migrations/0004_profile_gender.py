
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0003_profilephoto_embedding"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="gender",
            field=models.CharField(
                choices=[("male", "Erkak"), ("female", "Ayol")],
                default="male",
                max_length=10,
                verbose_name="Jinsi",
            ),
            preserve_default=False,
        ),
    ]
