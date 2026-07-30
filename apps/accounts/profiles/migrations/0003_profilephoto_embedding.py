
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profilephoto",
            name="embedding",
            field=models.JSONField(
                blank=True, null=True, verbose_name="Yuz embedding vektori"
            ),
        ),
    ]
