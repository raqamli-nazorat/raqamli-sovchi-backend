from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0011_alter_profile_candidate_type_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="bio",
            field=models.TextField(
                blank=True, null=True, verbose_name="O'zi haqida qo'shimcha ma'lumot"
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="children_count",
            field=models.PositiveSmallIntegerField(
                default=0, verbose_name="Farzandlar soni"
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="expectations",
            field=models.TextField(
                blank=True, null=True, verbose_name="Juftidan kutilayotgan talablar"
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="has_children",
            field=models.BooleanField(default=False, verbose_name="Farzandi bormi"),
        ),
        migrations.AlterField(
            model_name="profile",
            name="voice_intro",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="voice_intros/",
                verbose_name="Ovozli ko'rishuv xabari",
            ),
        ),
    ]
