from django.db import migrations


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("users", "0009_fix_fields"),
    ]

    operations = [
        migrations.RunPython(noop, reverse_code=noop),
    ]
