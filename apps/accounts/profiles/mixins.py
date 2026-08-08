import os

from rest_framework import serializers


MAX_VOICE_INTRO_BYTES = 1024 * 1024
ALLOWED_VOICE_EXTENSIONS = {".aac", ".m4a"}
ALLOWED_VOICE_MIME_TYPES = {"audio/aac", "audio/mp4", "audio/x-m4a"}


class VoiceIntroValidationMixin:
    def validate_voice_intro(self, value):
        if not value:
            return value

        extension = os.path.splitext(value.name)[1].lower()
        content_type = getattr(value, "content_type", None)
        if extension not in ALLOWED_VOICE_EXTENSIONS:
            raise serializers.ValidationError(
                "Faqat AAC yoki M4A ovoz fayli qabul qilinadi.",
                code="voice_type",
            )
        if content_type and content_type.lower() not in ALLOWED_VOICE_MIME_TYPES:
            raise serializers.ValidationError(
                "Ovoz faylining MIME turi qo'llab-quvvatlanmaydi.",
                code="voice_mime",
            )
        if value.size > MAX_VOICE_INTRO_BYTES:
            raise serializers.ValidationError(
                "Ovoz fayli 1 MB dan katta bo'lmasligi kerak.",
                code="voice_size",
            )
        return value
