from django.contrib.auth.models import AbstractUser, Permission
from django.db import models

from apps.accounts.users.managers import UserManager
from apps.accounts.users.mixins import RolePermissionsMixin
from apps.core.base.models import BaseModel
from apps.core.utils.validators import phone_validator


class UserRole(models.TextChoices):
    GROOM = "groom", "Kuyov"
    BRIDE = "bride", "Kelin"
    REPRESENTATIVE = "representative", "Vakil"


class AuthProvider(models.TextChoices):
    GOOGLE = "google", "Google"
    PHONE = "phone", "Phone"
    TELEGRAM = "telegram", "Telegram"
    EMAIL = "email", "Email"


class Role(BaseModel):
    name = models.CharField(max_length=150, unique=True, verbose_name="Nomi")
    is_default = models.BooleanField(
        default=False,
        verbose_name="Boshlang'ich rol",
        help_text="Yangi ro'yxatdan o'tgan foydalanuvchilarga avtomatik beriladigan rol",
    )
    permissions = models.ManyToManyField(
        Permission,
        verbose_name="Huquqlar",
        blank=True,
    )

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Rollar"
        constraints = [
            models.UniqueConstraint(
                fields=["is_default"],
                condition=models.Q(is_default=True),
                name="unique_default_role",
            )
        ]

    def save(self, *args, **kwargs):
        if self.is_default:
            Role.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.is_active = False
        self.save()

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name


class User(AbstractUser, RolePermissionsMixin, BaseModel):
    username = None
    groups = None

    phone_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        validators=[phone_validator],
        verbose_name="Telefon raqam",
    )
    email = models.EmailField(
        blank=True, null=True, unique=True, verbose_name="Email manzili"
    )
    auth_provider = models.CharField(
        max_length=20,
        choices=AuthProvider.choices,
        default=AuthProvider.PHONE,
        verbose_name="Ro'yxatdan o'tgan usuli",
    )
    is_verified = models.BooleanField(
        default=False, verbose_name="Tasdiqlangan foydalanuvchi"
    )
    is_blocked = models.BooleanField(
        default=False, verbose_name="Bloklangan foydalanuvchi"
    )

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        db_table = "users"

    def __str__(self):
        identifier = self.phone_number or self.email or str(self.id)
        return f"{identifier} ({self.get_auth_provider_display()})"


class UserPledge(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="pledge",
        verbose_name="Foydalanuvchi",
    )
    accepted_terms = models.BooleanField(
        default=False, verbose_name="Shartlarga roziligi"
    )
    has_serious_badge = models.BooleanField(
        default=False, verbose_name="'Niyati jiddiy' belgisi"
    )
    ip_address = models.GenericIPAddressField(
        blank=True, null=True, verbose_name="IP manzil"
    )

    class Meta:
        verbose_name = "Halollik roziligi (Pledge)"
        verbose_name_plural = "Halollik roziliklari (Pledges)"
        db_table = "user_pledges"

    def __str__(self):
        return f"{self.user.phone_number} - Badge: {self.has_serious_badge}"
