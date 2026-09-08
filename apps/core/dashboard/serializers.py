"""Boshqaruv paneli javobining tuzilishi (asosan Swagger hujjati uchun)."""

from rest_framework import serializers


class UsersMetricSerializer(serializers.Serializer):
    """Jami foydalanuvchilar koʻrsatkichi."""

    value = serializers.IntegerField()
    delta_week = serializers.IntegerField()


class ProfilesMetricSerializer(serializers.Serializer):
    """Anketa toʻldirganlar koʻrsatkichi."""

    value = serializers.IntegerField()
    conversion_pct = serializers.IntegerField()


class ActiveChatsMetricSerializer(serializers.Serializer):
    """Faol suhbatlar koʻrsatkichi."""

    value = serializers.IntegerField()


class MarriedMetricSerializer(serializers.Serializer):
    """Nikohga yetganlar koʻrsatkichi (hozircha modeli yoʻq — 0 / null)."""

    value = serializers.IntegerField()
    delta_month = serializers.IntegerField(allow_null=True)


class TotalsSerializer(serializers.Serializer):
    """Yuqori qatordagi 4 ta asosiy raqam."""

    users = UsersMetricSerializer()
    profiles_filled = ProfilesMetricSerializer()
    active_chats = ActiveChatsMetricSerializer()
    married = MarriedMetricSerializer()


class TrendSerializer(serializers.Serializer):
    """Soʻralgan oraliqdagi kunlik dinamika (parallel massivlar)."""

    days = serializers.ListField(child=serializers.DateField())
    registrations = serializers.ListField(child=serializers.IntegerField())
    questionnaires = serializers.ListField(child=serializers.IntegerField())
    matches = serializers.ListField(child=serializers.IntegerField())


class FunnelSerializer(serializers.Serializer):
    """Anketa toʻldirish voronkasi bosqichlari."""

    registered = serializers.IntegerField()
    profile_filled = serializers.IntegerField()
    questions_done = serializers.IntegerField()
    request_sent = serializers.IntegerField()
    chat_started = serializers.IntegerField()


class TasksSerializer(serializers.Serializer):
    """Navbatdagi vazifalar sanoqlari (profile_moderation hozircha 0).

    Ochiq shikoyatlar va AI signallari sidebar badge'iga koʻchdi
    (`SidebarBadgesSerializer`).
    """

    profile_moderation = serializers.IntegerField()


class DashboardSummarySerializer(serializers.Serializer):
    """Boshqaruv paneli uchun umumlashgan javob."""

    totals = TotalsSerializer()
    trend = TrendSerializer()
    funnel = FunnelSerializer()
    tasks = TasksSerializer()


class SidebarBadgesSerializer(serializers.Serializer):
    """Sidebar menyu punktlari yonidagi badge sanoqlari.

    `ai_signals` hozircha modeli yoʻq — doim 0.
    """

    users = serializers.IntegerField()
    ai_signals = serializers.IntegerField()
    complaints_open = serializers.IntegerField()
    questions = serializers.IntegerField()
    psychologists = serializers.IntegerField()
