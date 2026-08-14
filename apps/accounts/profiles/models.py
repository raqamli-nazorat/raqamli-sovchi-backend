from decimal import Decimal
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point

from apps.accounts.users.models import User
from apps.core.base.models import BaseModel
from apps.core.locations.models import District, Region


class GenderType(models.TextChoices):
    MALE = "male", "Erkak"
    FEMALE = "female", "Ayol"


class HealthStatus(models.TextChoices):
    HEALTHY = "healthy", "Sog'lom"
    DISABLED = "disabled", "Nogironligi bor"


class CandidateRole(models.TextChoices):
    GROOM = "groom", "Kuyov"
    BRIDE = "bride", "Kelin"
    REPRESENTATIVE = "representative", "Vakil"


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
    candidate_type = models.CharField(
        max_length=20,
        choices=CandidateRole.choices,
        blank=True,
        null=True,
        verbose_name="Nomzod turi (Kuyov/Kelin/Vakil)",
    )
    birth_year = models.PositiveIntegerField(verbose_name="Tug'ilgan yili")
    height = models.PositiveIntegerField(verbose_name="Bo'yi (sm)")
    weight = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Vazni (kg)"
    )

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

    health_status = models.ForeignKey(
        "references.HealthStatus",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
        verbose_name="Sog'liq holati",
    )
    marital_status = models.ForeignKey(
        "references.MaritalStatus",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
        verbose_name="Oilaviy holati",
    )

    education_level = models.ForeignKey(
        "references.EducationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
        verbose_name="Ta'lim darajasi",
    )
    nationality = models.ForeignKey(
        "references.Nationality",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
        verbose_name="Millati",
    )
    profession = models.ForeignKey(
        "references.Profession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
        verbose_name="Kasbi",
    )
    has_children = models.BooleanField(default=False, verbose_name="Farzandi bormi")
    children_count = models.PositiveSmallIntegerField(
        default=0, verbose_name="Farzandlar soni"
    )
    expectations = models.TextField(
        blank=True, null=True, verbose_name="Juftidan kutilayotgan talablar"
    )

    bio = models.TextField(
        blank=True, null=True, verbose_name="O'zi haqida qo'shimcha ma'lumot"
    )
    voice_intro = models.FileField(
        upload_to="voice_intros/",
        blank=True,
        null=True,
        verbose_name="Ovozli ko'rishuv xabari",
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
    location = gis_models.PointField(
        geography=True,
        srid=4326,
        blank=True,
        null=True,
        verbose_name="GPS Nuqtasi (Location)",
    )
    blur_photos = models.BooleanField(
        default=True, verbose_name="Rasmlarni xiralashtirish (Blur)"
    )

    class Meta:
        verbose_name = "Profil Anketa"
        verbose_name_plural = "Profil Anketalari"
        db_table = "profiles"

    def save(self, *args, **kwargs):
        if self.latitude is not None and self.longitude is not None:
            try:
                point = Point(float(self.longitude), float(self.latitude), srid=4326)
                self.location = point
            except Exception:
                pass

        try:
            if self.location is not None and (
                self.latitude is None or self.longitude is None
            ):
                self.longitude = Decimal(str(self.location.x))
                self.latitude = Decimal(str(self.location.y))
        except Exception:
            pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


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
    kinship = models.ForeignKey(
        "references.Kinship",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="representatives",
        verbose_name="Qarindoshlik holati",
    )
    candidate_role = models.CharField(
        max_length=20,
        choices=[("groom", "Kuyov"), ("bride", "Kelin")],
        verbose_name="Vakillik qilayotgan nomzod turi (Kuyov/Kelin)",
    )
    candidate_contact = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Nomzodning telefon raqami yoki email manzili",
    )
    target_candidate = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="represented_by_infos",
        verbose_name="Biriktirilgan nomzod (User)",
    )
    is_approved = models.BooleanField(
        default=False,
        verbose_name="Nomzod tomonidan rozilik berilganmi?",
    )

    class Meta:
        verbose_name = "Vakil ma'lumoti"
        verbose_name_plural = "Vakil ma'lumotlari"
        db_table = "representative_infos"

    def __str__(self):
        return (
            f"Vakil: {self.profile.first_name} -> {self.candidate_contact or 'Nomzod'}"
        )


class SavedProfile(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="saved_profiles",
        verbose_name="Foydalanuvchi",
    )
    saved_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="saved_by_users",
        verbose_name="Saqlangan profil",
    )

    class Meta:
        verbose_name = "Saqlangan profil"
        verbose_name_plural = "Saqlangan profillar"
        db_table = "saved_profiles"
        unique_together = ("user", "saved_profile")

    def __str__(self):
        return f"{self.user} -> {self.saved_profile}"
