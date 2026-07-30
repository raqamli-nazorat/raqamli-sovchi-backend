from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_alter_user_auth_provider"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="pin_code",
        ),
    ]
