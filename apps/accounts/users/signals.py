from django.contrib.auth.models import Permission
from django.db.models.signals import post_save
from django.dispatch import receiver

DEFAULT_USER_PERMISSIONS_CODENAMES = [
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


@receiver(post_save, sender="users.User")
def assign_default_user_permissions(sender, instance, created, **kwargs):
    if created:
        perms = Permission.objects.filter(
            codename__in=DEFAULT_USER_PERMISSIONS_CODENAMES
        )
        if perms.exists():
            instance.user_permissions.add(*perms)
