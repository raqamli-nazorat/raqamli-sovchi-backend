from django.db import models
from apps.core.base.models import BaseModel
from apps.accounts.users.models import User
from apps.core.locations.models import Region, District


class GenderType(models.TextChoices):
    MALE = "male", "Erkak"
    FEMALE = "female", "Ayol"


class HealthStatus(models.TextChoices):
    HEALTHY = "healthy", "Sog'lom"
    DISABLED = "disabled", "Nogironligi bor"


class MaritalStatus(models.TextChoices):
    NEVER_MARRIED = "never_married", "Birinchi marta turmush qurmoqchi"
    DIVORCED = "divorced", "Ajrashgan"


class KinshipType(models.TextChoices):
    FATHER = "father", "Ota"
    MOTHER = "mother", "Ona"
    UNCLE_PATERNAL = "uncle_paternal", "Amaki"
    UNCLE_MATERNAL = "uncle_maternal", "Tog'a"
    AUNT_PATERNAL = "aunt_paternal", "Amma"
    AUNT_MATERNAL = "aunt_maternal", "Xola"
    OTHER = "other", "Boshqa qarindosh"


class Profile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Foydalanuvchi",
    )
    first_name = models.CharField(max_length=100, verbose_name="Ismi")
    last_name = models.CharField(max_length=100, verbose_name="Familiyasi")
    middle_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Otasining ismi"
    )
    gender = models.CharField(
        max_length=10,
        choices=GenderType.choices,
        verbose_name="Jinsi",
    )
    birth_year = models.PositiveIntegerField(verbose_name="Tug'ilgan yili")
    height = models.PositiveIntegerField(verbose_name="Bo'yi (sm)")
    weight = models.PositiveIntegerField(verbose_name="Vazni (kg)")

    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        related_name="profiles",
        verbose_name="Viloyat",
    )
    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        null=True,
        related_name="profiles",
        verbose_name="Tuman",
    )

    health_status = models.CharField(
        max_length=20,
        choices=HealthStatus.choices,
        default=HealthStatus.HEALTHY,
        verbose_name="Sog'liqlik darajasi",
    )
    marital_status = models.CharField(
        max_length=20, choices=MaritalStatus.choices, verbose_name="Oilaviy holati"
    )

    bio = models.TextField(blank=True, null=True, verbose_name="O'zi haqida izoh matn")
    voice_intro = models.FileField(
        upload_to="voice_intros/",
        blank=True,
        null=True,
        verbose_name="Anonim ovozli xabar (Audio)",
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="Kenglik (Latitude)",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="Uzunlik (Longitude)",
    )
    blur_photos = models.BooleanField(
        default=True, verbose_name="Rasmlarni xiralashtirish (Blur)"
    )

    class Meta:
        verbose_name = "Profil Anketa"
        verbose_name_plural = "Profil Anketalari"
        db_table = "profiles"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user.get_role_display()})"


class ProfilePhoto(BaseModel):
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="photos", verbose_name="Profil"
    )
    image = models.ImageField(upload_to="profile_photos/", verbose_name="Rasm")
    embedding = models.JSONField(
        blank=True, null=True, verbose_name="Yuz embedding vektori"
    )
    order = models.PositiveSmallIntegerField(default=1, verbose_name="Tartib")
    is_main = models.BooleanField(default=False, verbose_name="Asosiy rasm")

    class Meta:
        verbose_name = "Profil rasmi"
        verbose_name_plural = "Profil rasmlari"
        ordering = ["order"]
        db_table = "profile_photos"

    def __str__(self):
        return f"{self.profile.first_name} photo #{self.order}"


class RepresentativeInfo(BaseModel):
    profile = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name="representative_info",
        verbose_name="Vakil profili",
    )
    kinship = models.CharField(
        max_length=30, choices=KinshipType.choices, verbose_name="Qarindoshlik holati"
    )
    candidate_role = models.CharField(
        max_length=20,
        choices=[("groom", "Kuyov"), ("bride", "Kelin")],
        verbose_name="Nomzod turi",
    )

    class Meta:
        verbose_name = "Vakil ma'lumoti"
        verbose_name_plural = "Vakil ma'lumotlari"
        db_table = "representative_infos"

    def __str__(self):
        return f"Vakil: {self.profile.first_name} ({self.get_kinship_display()})"
