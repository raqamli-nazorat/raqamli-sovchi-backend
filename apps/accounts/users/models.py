from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.base.models import BaseModel
from apps.accounts.users.managers import UserManager


class AuthProvider(models.TextChoices):
    GOOGLE = "google", "Google"
    PHONE = "phone", "Phone"
    TELEGRAM = "telegram", "Telegram"



class UserRole(models.TextChoices):
    GROOM = "groom", "Kuyov"
    BRIDE = "bride", "Kelin"
    REPRESENTATIVE = "representative", "Vakil"


class User(AbstractUser, BaseModel):
    username = None
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name="Telefon raqam"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        unique=True,
        verbose_name="Email manzili"
    )
    auth_provider = models.CharField(
        max_length=20,
        choices=AuthProvider.choices,
        default=AuthProvider.PHONE,
        verbose_name="Ro'yxatdan o'tgan usuli"
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        blank=True,
        null=True,
        verbose_name="Foydalanuvchi roli (Kuyov/Kelin/Vakil)"
    )
    pin_code = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name="PIN-kod HASH"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Tasdiqlangan foydalanuvchi"
    )

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        db_table = "users"

    def __str__(self):
        return f"{self.phone_number} ({self.get_auth_provider_display()})"


class UserPledge(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="pledge",
        verbose_name="Foydalanuvchi"
    )
    accepted_terms = models.BooleanField(
        default=False,
        verbose_name="Shartlarga roziligi"
    )
    has_serious_badge = models.BooleanField(
        default=False,
        verbose_name="'Niyati jiddiy' belgisi"
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="IP manzil"
    )

    class Meta:
        verbose_name = "Halollik roziligi (Pledge)"
        verbose_name_plural = "Halollik roziliklari (Pledges)"
        db_table = "user_pledges"

    def __str__(self):
        return f"{self.user.phone_number} - Badge: {self.has_serious_badge}"
