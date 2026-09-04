"""Test nomzodlari uchun umumiy sozlamalar va butunlay o'chirish (teardown) logikasi.

Faylnomi `_` bilan boshlangani uchun Django uni alohida buyruq sifatida yuklamaydi —
`seed_test_candidates` va `unseed_test_candidates` buyruqlari shu moduldan foydalanadi.
"""

# Barcha test userlarning telefon prefiksi. Bu — yagona marker: o'chirishda
# aynan shu prefiks bo'yicha topiladi. Format phone_validator ga mos: ^\+998\d{9}$
# Masalan +998900000042  ( +998 + "90000" + "0042" ).
TEST_PHONE_PREFIX = "+99890000"

# Barcha nomzod va vakillar shu viloyatga biriktiriladi.
REGION_NAME = "Farg'ona viloyati"


def test_user_qs():
    """Test userlarning QuerySet-ini (telefon prefiksi bo'yicha) qaytaradi."""
    from apps.accounts.users.models import User

    return User.objects.filter(phone_number__startswith=TEST_PHONE_PREFIX)


def delete_test_data(stdout=None):
    """Barcha test user va ularga bog'liq ma'lumotlarni butunlay (hard delete) o'chiradi.

    O'chirish tartibi muhim: `Notification` va `notifications.UserDevice` da
    `user` uchun `on_delete=PROTECT` — ular userdan oldin o'chirilishi shart.
    Qolganlari (`Profile`, `UserAnswer`, `ProfilePhoto`, `UserPledge`,
    `RepresentativeInfo`, `users.UserDevice`, `SavedProfile`, `BlockedUser`,
    `MatchRequest` -> `ChatRoom` -> `Message`, `PhotoRequest`) cascade bilan ketadi.

    :param stdout: Ixtiyoriy oqim (management buyruq `self.stdout`) — jarayon logi uchun.
    :return: O'chirilgan test userlar soni (int).
    """
    from auditlog.context import disable_auditlog
    from auditlog.models import LogEntry
    from django.db import transaction

    from apps.accounts.notifications.models import Notification
    from apps.accounts.notifications.models import UserDevice as NotificationDevice
    from apps.accounts.profiles.models import ProfilePhoto
    from apps.accounts.users.models import User

    user_ids = list(test_user_qs().values_list("id", flat=True))

    with disable_auditlog(), transaction.atomic():
        # 1) Media fayllar (S3 yoki lokal — storage API bir xil). Row o'chishidan oldin.
        for photo in ProfilePhoto.objects.filter(profile__user_id__in=user_ids):
            try:
                photo.image.delete(save=False)
            except Exception:
                pass

        # 2) PROTECT bog'lanishlar — userdan oldin.
        Notification.objects.filter(user_id__in=user_ids).hard_delete()
        NotificationDevice.objects.filter(user_id__in=user_ids).hard_delete()

        # 3) Userlar — qolgan hamma narsa cascade bilan o'chadi.
        User.objects.filter(id__in=user_ids).hard_delete()

        # 4) Auditlog qoldig'i. `object_pk` — oddiy matn maydoni, FK emas,
        #    shuning uchun cascade bo'lmaydi va qo'lda tozalanadi.
        LogEntry.objects.filter(object_pk__in=[str(pk) for pk in user_ids]).delete()

    # 5) Seed yarmida uzilib qolsa (transaction rollback), DB roldan qaytadi-yu,
    #    diskka yozilgan rasm fayllari qoladi. "seed_" prefiksli fayllarni nomi
    #    bo'yicha yakuniy tozalash.
    orphan_files = _sweep_seed_photo_files()

    if stdout:
        stdout.write(
            f"{len(user_ids)} ta test user o'chirildi; "
            f"{orphan_files} ta qo'shimcha rasm fayli tozalandi."
        )
    return len(user_ids)


def _sweep_seed_photo_files():
    """`profile_photos/` katalogidagi `seed_` prefiksli barcha fayllarni o'chiradi."""
    from django.core.files.storage import default_storage

    removed = 0
    try:
        _dirs, files = default_storage.listdir("profile_photos")
    except Exception:
        return removed

    for name in files:
        if name.startswith("seed_"):
            try:
                default_storage.delete(f"profile_photos/{name}")
                removed += 1
            except Exception:
                pass
    return removed
