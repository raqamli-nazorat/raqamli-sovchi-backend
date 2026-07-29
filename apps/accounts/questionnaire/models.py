from django.db import models
from apps.core.base.models import BaseModel
from apps.accounts.profiles.models import Profile


class SectionType(models.TextChoices):
    RELIGIOUS_SPIRITUAL = "religious_spiritual", "I. Diniy-Ma'naviy Qadriyatlar va E'tiqod"
    FINANCIAL_GOVERNANCE = "financial_governance", "II. Oila Boshqaruvi va Moliyaviy Qarashlar"
    RELATIVES_RELATIONS = "relatives_relations", "III. Qarindoshlar va Qaynona-Kelin Munosabatlari"
    CHARACTER_CRISIS = "character_crisis", "IV. Harakter, Psixologik Muvofiqlik va Inqiroz"
    FUTURE_PLANS = "future_plans", "V. Kelajak Rejalari va Maishiy Hayot"


class TargetGender(models.TextChoices):
    ALL = "all", "Barchaga (Umumiy)"
    GROOM = "groom", "Faqat Kuyov uchun"
    BRIDE = "bride", "Faqat Kelin uchun"


class Question(BaseModel):
    section = models.CharField(
        max_length=50,
        choices=SectionType.choices,
        verbose_name="Bo'lim"
    )
    text = models.TextField(verbose_name="Savol matni")
    target_gender = models.CharField(
        max_length=10,
        choices=TargetGender.choices,
        default=TargetGender.ALL,
        verbose_name="Qaysi jins uchun"
    )
    is_trap_question = models.BooleanField(
        default=False,
        verbose_name="Tizim tuzoq savolimi (Lie Scale / Cross Validation)"
    )
    order = models.PositiveIntegerField(default=1, verbose_name="Tartib raqami")

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        ordering = ["order"]
        db_table = "questions"

    def __str__(self):
        return f"{self.order}. {self.text[:50]}..."


class QuestionOption(BaseModel):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name="Savol"
    )
    option_letter = models.CharField(
        max_length=2,
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
        verbose_name="Variant harfi (A/B/C/D)"
    )
    text = models.TextField(verbose_name="Variant matni")
    weight = models.IntegerField(
        default=0,
        verbose_name="Variant balli/og'irligi (Algoritm va Lie Scale uchun)"
    )

    class Meta:
        verbose_name = "Savol varianti"
        verbose_name_plural = "Savol variantlari"
        ordering = ["option_letter"]
        unique_together = ("question", "option_letter")
        db_table = "question_options"

    def __str__(self):
        return f"{self.question.order}-{self.option_letter}: {self.text[:40]}"


class UserAnswer(BaseModel):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Profil"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="user_answers",
        verbose_name="Savol"
    )
    selected_option = models.ForeignKey(
        QuestionOption,
        on_delete=models.CASCADE,
        related_name="selected_by_users",
        verbose_name="Tanlangan variant"
    )

    class Meta:
        verbose_name = "Foydalanuvchi javobi"
        verbose_name_plural = "Foydalanuvchi javoblari"
        unique_together = ("profile", "question")
        db_table = "user_answers"

    def __str__(self):
        return f"{self.profile.first_name} - Savol {self.question.order}: {self.selected_option.option_letter}"
