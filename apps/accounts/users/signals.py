from django.contrib.auth.models import Permission
from django.db import OperationalError, ProgrammingError
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from apps.accounts.users.models import Role, User

DEFAULT_PERMISSIONS_CODENAMES = [
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


@receiver(post_migrate)
def create_default_role_after_migration(sender, **kwargs):
    if sender.name == "apps.accounts.users":
        try:
            role = Role.objects.filter(is_default=True).first()
            if not role:
                role = Role.objects.first()
                if role:
                    role.is_default = True
                    role.save(update_fields=["is_default"])
                else:
                    role = Role.objects.create(name="Foydalanuvchi", is_default=True)

            if role and role.permissions.count() == 0:
                perms = Permission.objects.filter(
                    codename__in=DEFAULT_PERMISSIONS_CODENAMES
                )
                if perms.exists():
                    role.permissions.set(perms)
        except (ProgrammingError, OperationalError):
            pass


@receiver(post_save, sender=User)
def assign_default_user_role(sender, instance, created, **kwargs):
    if created and not instance.role_id:
        try:
            role = Role.objects.filter(is_default=True).first()
            if not role:
                role = Role.objects.first()
                if role:
                    role.is_default = True
                    role.save(update_fields=["is_default"])
                else:
                    role = Role.objects.create(name="Foydalanuvchi", is_default=True)

            if role:
                instance.role = role
                instance.save(update_fields=["role"])
        except (ProgrammingError, OperationalError):
            pass
