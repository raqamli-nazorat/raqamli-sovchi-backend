from django.contrib.auth.models import Permission
from django.db import OperationalError, ProgrammingError
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from apps.accounts.users.models import Role, User

DEFAULT_PERMISSIONS_CODENAMES = [
    # Profiles & Candidates
    "view_profile",
    "change_me_profile",
    "delete_me_profile",
    "add_profilephoto",
    "change_profilephoto",
    "delete_profilephoto",
    "view_profilephoto",
    "add_representativeinfo",
    "change_representativeinfo",
    "delete_representativeinfo",
    "view_representativeinfo",
    # User Pledge
    "add_userpledge",
    "change_userpledge",
    "view_userpledge",
    # References (Read-only for default users)
    "view_region",
    "view_district",
    "view_educationlevel",
    "view_nationality",
    "view_profession",
    "view_maritalstatus",
    "view_healthstatus",
    # Questionnaire
    "view_sectiontype",
    "view_question",
    "view_questionoption",
    "add_useranswer",
    "change_useranswer",
    "delete_useranswer",
    "view_useranswer",
    # Matches & Chats
    "add_matchrequest",
    "change_matchrequest",
    "delete_matchrequest",
    "view_matchrequest",
    "add_chatroom",
    "change_chatroom",
    "view_chatroom",
    "add_message",
    "change_message",
    "delete_message",
    "view_message",
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

            if role:
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
