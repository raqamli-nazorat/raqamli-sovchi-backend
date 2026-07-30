from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_remove_user_role_fix_permissions"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="groups",
        ),
    ]
