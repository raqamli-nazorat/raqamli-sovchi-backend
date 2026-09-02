from rest_framework import serializers

from apps.core.base.serializers import BaseModelSerializer

from .models import MatchRequest, MatchRequestStatus


class MatchRequestSerializer(BaseModelSerializer):
    class Meta:
        model = MatchRequest
        fields = "__all__"
        # from_profile doim so'rov yuborayotgan foydalanuvchidan olinadi —
        # mijoz uni yuborib, boshqa odam nomidan so'rov qila olmasligi kerak.
        # Holat esa faqat accept/ va reject/ amallari orqali o'zgaradi:
        # u yerda egalik tekshiruvi bor.
        read_only_fields = ["from_profile", "status", "visibility_scope"]
        related_fields = {
            "from_profile": ["id", "first_name", "last_name"],
            "to_profile": ["id", "first_name", "last_name"],
            "question": ["id", "order", "text"],
        }

    def validate_to_profile(self, value):
        """
        Ushbu nomzodga so'rov yuborish mumkinligini tekshiradi.

        Uchta holat taqiqlanadi: o'ziga so'rov yuborish; ko'rish huquqi yo'q
        anketaga (jinsi mos kelmagan yoki o'zaro bloklangan) so'rov yuborish;
        hali ko'rib chiqilmagan so'rovni takrorlash.

        :param value: Nishon anketa (Profile).
        :return: Tekshiruvdan o'tgan anketa (Profile).
        """
        if self.instance is not None:
            return value

        request = self.context.get("request")
        user = getattr(request, "user", None)
        profile = getattr(user, "profile", None)
        if not profile:
            return value

        if value.id == profile.id:
            raise serializers.ValidationError(
                "O'zingizga moslik so'rovini yubora olmaysiz."
            )

        from apps.accounts.profiles.models import Profile
        from apps.accounts.profiles.services import filter_profiles_for_user

        allowed = filter_profiles_for_user(Profile.objects.active(), user)
        if not allowed.filter(pk=value.pk).exists():
            raise serializers.ValidationError(
                "Ushbu nomzodga so'rov yuborish mumkin emas."
            )

        undecided = (
            MatchRequestStatus.PENDING,
            MatchRequestStatus.FORWARDED_TO_REPRESENTATIVE,
        )
        if (
            MatchRequest.objects.active()
            .filter(from_profile=profile, to_profile=value, status__in=undecided)
            .exists()
        ):
            raise serializers.ValidationError(
                "Bu nomzodga yuborgan so'rovingiz hali ko'rib chiqilmoqda."
            )

        return value
