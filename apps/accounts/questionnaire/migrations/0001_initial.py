import uuid
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("profiles", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SectionType",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("name", models.CharField(max_length=255, unique=True, verbose_name="Nomi")),
            ],
            options={
                "verbose_name": "Savol bo'limi",
                "verbose_name_plural": "Savol bo'limlari",
                "db_table": "section_types",
            },
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="questionnaire.sectiontype", verbose_name="Bo'lim")),
                ("text", models.TextField(verbose_name="Savol matni")),
                ("target_gender", models.CharField(choices=[("all", "Barchaga (Umumiy)"), ("groom", "Faqat Kuyov uchun"), ("bride", "Faqat Kelin uchun")], default="all", max_length=10, verbose_name="Qaysi jins uchun")),
                ("is_trap_question", models.BooleanField(default=False, verbose_name="Tizim tuzoq savolimi (Lie Scale / Cross Validation)")),
                ("order", models.PositiveIntegerField(default=1, verbose_name="Tartib raqami")),
            ],
            options={
                "verbose_name": "Savol",
                "verbose_name_plural": "Savollar",
                "ordering": ["order"],
                "db_table": "questions",
            },
        ),
        migrations.CreateModel(
            name="QuestionOption",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="options", to="questionnaire.question", verbose_name="Savol")),
                ("option_letter", models.CharField(choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")], max_length=2, verbose_name="Variant harfi (A/B/C/D)")),
                ("text", models.TextField(verbose_name="Variant matni")),
                ("weight", models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)], verbose_name="Variant balli/og'irligi (0-10)")),
            ],
            options={
                "verbose_name": "Savol varianti",
                "verbose_name_plural": "Savol variantlari",
                "ordering": ["option_letter"],
                "db_table": "question_options",
            },
        ),
        migrations.AlterUniqueTogether(
            name="questionoption",
            unique_together={("question", "option_letter")},
        ),
        migrations.CreateModel(
            name="UserAnswer",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yaratilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="profiles.profile", verbose_name="Profil")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_answers", to="questionnaire.question", verbose_name="Savol")),
                ("selected_option", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="selected_by_users", to="questionnaire.questionoption", verbose_name="Tanlangan variant")),
            ],
            options={
                "verbose_name": "Foydalanuvchi javobi",
                "verbose_name_plural": "Foydalanuvchi javoblari",
                "db_table": "user_answers",
            },
        ),
        migrations.AlterUniqueTogether(
            name="useranswer",
            unique_together={("profile", "question")},
        ),
    ]
