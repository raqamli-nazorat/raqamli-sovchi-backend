from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("users", "0009_fix_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="is_default",
            field=models.BooleanField(
                default=False,
                help_text="Yangi ro'yxatdan o'tgan foydalanuvchilarga avtomatik beriladigan rol",
                verbose_name="Boshlang'ich rol",
            ),
        ),
        migrations.AddConstraint(
            model_name="role",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_default", True)),
                fields=("is_default",),
                name="unique_default_role",
            ),
        ),
    ]
