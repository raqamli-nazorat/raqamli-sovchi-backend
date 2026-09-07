from django.core.management.base import BaseCommand

from apps.accounts.complaints.models import (
    Complaint,
    ComplaintEnforcementAction,
    ComplaintStatus,
)
from apps.accounts.users.services import block_user


class Command(BaseCommand):
    """
    `approved` + `block` chorasi qo'llangan, lekin foydalanuvchisi hali
    bloklanmagan shikoyatlarni topib, foydalanuvchini bloklaydi.

    Enforcement oqimi mavjud bo'lmagan davrda hal qilingan yoki Django admin
    orqali qo'lda tasdiqlangan eski shikoyatlar tufayli yuzaga kelgan
    nomuvofiqlikni tuzatish uchun bir marta ishga tushiriladi.
    """

    help = (
        "approved + block bo'lgan, lekin foydalanuvchisi bloklanmagan "
        "shikoyatlar bo'yicha foydalanuvchini bloklaydi"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Faqat nomuvofiqliklarni ko'rsatadi, hech nima o'zgartirmaydi",
        )

    def handle(self, *args, **options):
        """Nomuvofiq shikoyatlarni topadi va (dry-run bo'lmasa) tuzatadi."""
        dry_run = options["dry_run"]

        queryset = Complaint.objects.filter(
            status=ComplaintStatus.APPROVED,
            enforcement_action=ComplaintEnforcementAction.BLOCK,
            to_user__is_blocked=False,
        ).select_related("to_user")

        total = queryset.count()
        self.stdout.write(f"Nomuvofiq shikoyatlar: {total} ta")

        fixed = 0
        for complaint in queryset:
            user = complaint.to_user
            label = user.phone_number or user.email or str(user.id)
            self.stdout.write(f"  - complaint={complaint.id} | user={label}")
            if not dry_run:
                block_user(
                    user,
                    reason=complaint.get_reason_display(),
                    notify_user=False,
                )
                fixed += 1

        if dry_run:
            self.stdout.write(self.style.WARNING("dry-run: hech nima o'zgartirilmadi"))
        else:
            self.stdout.write(self.style.SUCCESS(f"{fixed} ta foydalanuvchi bloklandi"))
