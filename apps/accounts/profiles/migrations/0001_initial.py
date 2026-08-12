import uuid
import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("locations", "0001_initial"),
        ("references", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL, verbose_name="Foydalanuvchi")),
                ("first_name", models.CharField(max_length=100, verbose_name="Ismi")),
                ("last_name", models.CharField(max_length=100, verbose_name="Familiyasi")),
                ("middle_name", models.CharField(blank=True, max_length=100, null=True, verbose_name="Otasining ismi")),
                ("gender", models.CharField(choices=[("male", "Erkak"), ("female", "Ayol")], max_length=10, verbose_name="Jinsi")),
                ("candidate_type", models.CharField(blank=True, choices=[("groom", "Kuyov"), ("bride", "Kelin"), ("representative", "Vakil")], max_length=20, null=True, verbose_name="Nomzod turi (Kuyov/Kelin/Vakil)")),
                ("birth_year", models.PositiveIntegerField(verbose_name="Tug'ilgan yili")),
                ("height", models.PositiveIntegerField(verbose_name="Bo'yi (sm)")),
                ("weight", models.PositiveIntegerField(blank=True, null=True, verbose_name="Vazni (kg)")),
                ("region", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="profiles", to="locations.region", verbose_name="Viloyat")),
                ("district", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="profiles", to="locations.district", verbose_name="Tuman")),
                ("health_status", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="profiles", to="references.healthstatus", verbose_name="Sog'liq holati")),
                ("marital_status", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="profiles", to="references.maritalstatus", verbose_name="Oilaviy holati")),
                ("education_level", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="profiles", to="references.educationlevel", verbose_name="Ta'lim darajasi")),
                ("nationality", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="profiles", to="references.nationality", verbose_name="Millati")),
                ("profession", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="profiles", to="references.profession", verbose_name="Kasbi")),
                ("has_children", models.BooleanField(default=False, verbose_name="Farzandi bormi")),
                ("children_count", models.PositiveSmallIntegerField(default=0, verbose_name="Farzandlar soni")),
                ("expectations", models.TextField(blank=True, null=True, verbose_name="Juftidan kutilayotgan talablar")),
                ("bio", models.TextField(blank=True, null=True, verbose_name="O'zi haqida qo'shimcha ma'lumot")),
                ("voice_intro", models.FileField(blank=True, null=True, upload_to="voice_intros/", verbose_name="Ovozli ko'rishuv xabari")),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="Kenglik (Latitude)")),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="Uzunlik (Longitude)")),
                ("location", django.contrib.gis.db.models.fields.PointField(blank=True, geography=True, null=True, srid=4326, verbose_name="GPS Nuqtasi (Location)")),
                ("blur_photos", models.BooleanField(default=True, verbose_name="Rasmlarni xiralashtirish (Blur)")),
            ],
            options={
                "verbose_name": "Profil Anketa",
                "verbose_name_plural": "Profil Anketalari",
                "db_table": "profiles",
            },
        ),
        migrations.CreateModel(
            name="ProfilePhoto",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="photos", to="profiles.profile", verbose_name="Profil")),
                ("image", models.ImageField(upload_to="profile_photos/", verbose_name="Rasm")),
                ("embedding", models.JSONField(blank=True, null=True, verbose_name="Yuz embedding vektori")),
                ("order", models.PositiveSmallIntegerField(default=1, verbose_name="Tartib")),
                ("is_main", models.BooleanField(default=False, verbose_name="Asosiy rasm")),
            ],
            options={
                "verbose_name": "Profil rasmi",
                "verbose_name_plural": "Profil rasmlari",
                "ordering": ["order"],
                "db_table": "profile_photos",
            },
        ),
        migrations.CreateModel(
            name="RepresentativeInfo",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("profile", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="representative_info", to="profiles.profile", verbose_name="Vakil profili")),
                ("kinship", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="representatives", to="references.kinship", verbose_name="Qarindoshlik holati")),
                ("candidate_role", models.CharField(choices=[("groom", "Kuyov"), ("bride", "Kelin")], max_length=20, verbose_name="Vakillik qilayotgan nomzod turi (Kuyov/Kelin)")),
                ("candidate_contact", models.CharField(blank=True, max_length=150, null=True, verbose_name="Nomzodning telefon raqami yoki email manzili")),
                ("target_candidate", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="represented_by_infos", to=settings.AUTH_USER_MODEL, verbose_name="Biriktirilgan nomzod (User)")),
                ("is_approved", models.BooleanField(default=False, verbose_name="Nomzod tomonidan rozilik berilganmi?")),
            ],
            options={
                "verbose_name": "Vakil ma'lumoti",
                "verbose_name_plural": "Vakil ma'lumotlari",
                "db_table": "representative_infos",
            },
        ),
    ]
