from django.contrib.auth.models import Permission
from django.db import OperationalError, ProgrammingError
from django.db.models.signals import post_migrate, post_save, pre_save
from django.dispatch import receiver

from apps.accounts.users.models import Role, User

DEFAULT_PERMISSIONS_CODENAMES = [
    # Profiles & Candidates (Read-only by default; self-management is handled via /me/)
    "view_profile",
    "view_profilephoto",
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
    # Vakil ro'yxatdan o'tishda qarindoshlik turini tanlaydi (RepresentativeInfo.kinship)
    "view_kinship",
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
    "add_photorequest",
    "change_photorequest",
    "delete_photorequest",
    "view_photorequest",
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
    """
    Boshlang'ich rolni yaratadi va unga oddiy foydalanuvchi huquqlarini beradi.

    Ataylab har bir app'ning post_migrate signalida ishlaydi: Django huquqlarni
    (Permission) har app uchun alohida yaratadi, shuning uchun faqat "users"
    app'ida ishlatilsa, keyingi app'larning huquqlari hali mavjud bo'lmaydi va
    rolga tushmay qoladi. Amal takroriy bajarilishga xavfsiz (idempotent) —
    oxirgi chaqiruvda huquqlar to'liq bo'ladi.
    """
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


@receiver(pre_save, sender=User)
def capture_is_blocked_transition(sender, instance, update_fields=None, **kwargs):
    """
    Saqlashdan oldin `is_blocked` maydoni o'zgarganini aniqlab, natijani
    `instance._is_blocked_transition` ga yozadi (True — bloklandi, False —
    blokdan chiqdi, None — o'zgarmadi). Yon ta'sirlarni `post_save`
    bajaradi.

    Bu tekshiruv har qanday saqlash yo'lida (API, Django admin, shell,
    data migration) ishlaydi — shu tufayli bloklash oqibatlari yagona
    joyda kafolatlanadi.
    """
    instance._is_blocked_transition = None

    if instance._state.adding:
        return
    if update_fields is not None and "is_blocked" not in update_fields:
        return

    old_is_blocked = (
        sender.objects.filter(pk=instance.pk)
        .values_list("is_blocked", flat=True)
        .first()
    )
    if old_is_blocked is not None and old_is_blocked != instance.is_blocked:
        instance._is_blocked_transition = instance.is_blocked


@receiver(post_save, sender=User)
def handle_is_blocked_transition(sender, instance, created, **kwargs):
    """
    `is_blocked` o'zgargan bo'lsa yon ta'sirlarni ishga tushiradi: yuzni
    qora ro'yxatga olish/tozalash va (so'ralgan bo'lsa) bildirishnoma.

    Sabab va bildirishnoma bayrog'i `block_user`/`unblock_user` tomonidan
    `instance` ga vaqtinchalik qo'yiladi; boshqa yo'llarda (masalan admin
    checkbox) ular bo'lmaydi va standart qiymatlar ishlatiladi.
    """
    transitioned_to = getattr(instance, "_is_blocked_transition", None)
    if transitioned_to is None:
        return

    instance._is_blocked_transition = None

    # Chaqiruvchi yon ta'sirni o'zi bajarmoqchi bo'lsa (masalan yuz tekshiruvi
    # aynan bir embeddingni qo'shishi kerak) — signal uni takrorlamaydi.
    if getattr(instance, "_skip_block_side_effects", False):
        return

    reason = getattr(instance, "_block_reason", None)
    notify_user = getattr(instance, "_block_notify", False)

    from apps.accounts.users.services import apply_user_block_side_effects

    apply_user_block_side_effects(
        instance,
        blocked=bool(transitioned_to),
        reason=reason,
        notify_user=notify_user,
    )
