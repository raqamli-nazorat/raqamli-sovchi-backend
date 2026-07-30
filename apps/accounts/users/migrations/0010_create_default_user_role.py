import uuid
from django.db import migrations


def create_default_user_role(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    Permission = apps.get_model("auth", "Permission")

    role, created = Role.objects.get_or_create(
        name="Foydalanuvchi",
        defaults={
            "id": uuid.uuid4(),
            "is_active": True,
        },
    )

    codenames = [
        "add_profile",
        "change_profile",
        "view_profile",
        "add_profilephoto",
        "change_profilephoto",
        "delete_profilephoto",
        "view_profilephoto",
        "add_representativeinfo",
        "change_representativeinfo",
        "view_representativeinfo",
        "add_userpledge",
        "change_userpledge",
        "view_userpledge",
        "add_questionnaire",
        "change_questionnaire",
        "view_questionnaire",
    ]

    perms = Permission.objects.filter(codename__in=codenames)
    if perms.exists():
        role.permissions.set(perms)


def remove_default_user_role(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    Role.objects.filter(name="Foydalanuvchi").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("users", "0009_fix_fields"),
    ]

    operations = [
        migrations.RunPython(create_default_user_role, reverse_code=remove_default_user_role),
    ]
