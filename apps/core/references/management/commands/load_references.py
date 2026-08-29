from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.references.models import (
    EducationLevel,
    HealthStatus,
    Kinship,
    MaritalStatus,
    Nationality,
    Profession,
)

# Har bir ma'lumotnoma uchun boshlang'ich qiymatlar.
# Ro'yxatlar ataylab qisqa: onboarding ekranlarida chip ko'rinishida
# chiqariladi, uzun ro'yxat o'sha dizaynni buzadi.
REFERENCE_DATA = {
    EducationLevel: [
        "O'rta",
        "O'rta maxsus",
        "Bakalavr",
        "Magistr",
        "Ilmiy daraja",
    ],
    Profession: [
        "Tibbiyot xodimi",
        "O'qituvchi",
        "Muhandis",
        "Dasturchi",
        "Iqtisodchi",
        "Huquqshunos",
        "Quruvchi",
        "Haydovchi",
        "Savdo xodimi",
        "Tadbirkor",
        "Harbiy/Huquq-tartibot xodimi",
        "Dizayner",
        "Marketing mutaxassisi",
        "Ishlab chiqarish xodimi",
        "Xizmat ko'rsatish sohasi",
        "Talaba",
        "Uy bekasi",
        "Boshqa",
    ],
    Nationality: [
        "O'zbek",
        "Qoraqalpoq",
        "Tojik",
        "Qozoq",
        "Qirg'iz",
        "Turkman",
        "Rus",
        "Tatar",
        "Koreys",
        "Boshqa",
    ],
    MaritalStatus: [
        "Turmush qurmagan",
        "Ajrashgan",
        "Beva",
    ],
    HealthStatus: [
        "Sog'lom",
        "Surunkali kasalligi bor",
        "Nogironligi bor",
    ],
    Kinship: [
        "Otasi",
        "Onasi",
        "Akasi",
        "Opasi",
        "Amakisi",
        "Tog'asi",
        "Ammasi",
        "Xolasi",
        "Bobosi",
        "Buvisi",
        "Boshqa qarindoshi",
    ],
}


class Command(BaseCommand):
    help = (
        "Ma'lumotnomalarni (ta'lim darajasi, kasb, millat, oilaviy holat, "
        "sog'liq holati, qarindoshlik) bazaga yuklaydi."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        """
        Har bir ma'lumotnoma jadvalini boshlang'ich qiymatlar bilan to'ldiradi.

        Buyruq takroriy ishga tushirilishga xavfsiz: mavjud yozuvlar
        get_or_create orqali qayta yaratilmaydi va o'zgartirilmaydi.

        :return: None
        """
        total_created = 0

        for model, names in REFERENCE_DATA.items():
            created_count = 0

            for name in names:
                _, created = model.objects.get_or_create(name=name)
                if created:
                    created_count += 1

            total_created += created_count
            self.stdout.write(
                f"{model._meta.verbose_name_plural}: "
                f"{created_count} ta yangi, jami {model.objects.count()} ta"
            )

        self.stdout.write(
            self.style.SUCCESS(f"Tayyor! Jami {total_created} ta yangi yozuv qo'shildi.")
        )
