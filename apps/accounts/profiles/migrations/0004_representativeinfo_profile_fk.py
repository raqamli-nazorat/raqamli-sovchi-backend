import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0003_savedprofile"),
    ]

    operations = [
        migrations.AlterField(
            model_name="representativeinfo",
            name="profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="representative_infos",
                to="profiles.profile",
                verbose_name="Vakil profili",
            ),
        ),
    ]
