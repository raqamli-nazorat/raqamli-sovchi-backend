"""Barcha test nomzod va vakillarni (seed_test_candidates yaratganlarni) butunlay o'chiradi.

Marker — telefon prefiksi (`_seed_common.TEST_PHONE_PREFIX`). Boshqa hech qanday
yozuvga tegmaydi. Media fayllar, PROTECT bog'lanishlar va auditlog qoldig'i ham tozalanadi.

Ishlatish:
    python manage.py unseed_test_candidates
"""

from django.core.management.base import BaseCommand

from ._seed_common import delete_test_data


class Command(BaseCommand):
    help = "Barcha test nomzod/vakillarni va ularga bog'liq ma'lumotlarni butunlay o'chiradi."

    def handle(self, *args, **options):
        deleted = delete_test_data(self.stdout)
        self.stdout.write(
            self.style.SUCCESS(f"Tayyor. {deleted} ta test user o'chirildi.")
        )
