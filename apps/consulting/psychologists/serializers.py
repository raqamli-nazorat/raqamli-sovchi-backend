from rest_framework import serializers

from apps.core.base.serializers import BaseModelSerializer

from .models import Psychologist


class PsychologistSerializer(BaseModelSerializer):
    """Psixolog CRUD uchun. Yozishda `first_name`/`last_name` alohida,
    o'qishda `full_name` qo'shimcha qaytadi."""

    full_name = serializers.ReadOnlyField()
    rating = serializers.SerializerMethodField()
    consultations_count = serializers.SerializerMethodField()
    next_session_at = serializers.SerializerMethodField()

    class Meta:
        model = Psychologist
        fields = "__all__"

    def get_rating(self, obj) -> float | None:
        """O'rtacha reyting. Suhbat (Consultation) modeli qo'shilgach to'ldiriladi."""
        return None

    def get_consultations_count(self, obj) -> int:
        """Suhbatlar soni. Suhbat modeli qo'shilgach to'ldiriladi."""
        return 0

    def get_next_session_at(self, obj) -> str | None:
        """Keyingi sessiya vaqti. Suhbat modeli qo'shilgach to'ldiriladi."""
        return None

    def validate_phone_number(self, value):
        """Telefon raqam boshqa psixologda ishlatilmaganini tekshiradi."""
        qs = Psychologist.objects.filter(phone_number=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu telefon raqam allaqachon ro'yxatdan o'tgan."
            )
        return value

    def validate_price(self, value):
        """Narx musbat bo'lishi shart."""
        if value <= 0:
            raise serializers.ValidationError("Narx 0 dan katta bo'lishi kerak.")
        return value

    def validate_session_duration_minutes(self, value):
        """Sessiya davomiyligi mantiqiy oraliqda (10–240 daqiqa)."""
        if not 10 <= value <= 240:
            raise serializers.ValidationError(
                "Sessiya davomiyligi 10 dan 240 daqiqagacha bo'lishi kerak."
            )
        return value
