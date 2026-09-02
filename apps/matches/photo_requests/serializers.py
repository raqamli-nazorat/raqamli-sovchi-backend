from rest_framework import serializers

from apps.core.base.serializers import BaseModelSerializer

from .models import PhotoRequest, PhotoRequestStatus


class PhotoRequestSerializer(BaseModelSerializer):
    class Meta:
        model = PhotoRequest
        fields = "__all__"
        read_only_fields = ["from_profile", "status"]
        related_fields = {
            "from_profile": ["id", "first_name", "last_name"],
            "to_profile": ["id", "first_name", "last_name"],
        }

    def validate_to_profile(self, value):
        """
        Ushbu nomzodga so'rov yuborish mumkinligini tekshiradi.

        O'ziga so'rov yuborish, ko'rish huquqi yo'q anketaga so'rov yuborish
        va takroriy kutilayotgan so'rov yuborish taqiqlanadi.

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
                "O'zingizga rasm so'rovini yubora olmaysiz."
            )

        from apps.accounts.profiles.models import Profile
        from apps.accounts.profiles.services import filter_profiles_for_user

        allowed = filter_profiles_for_user(Profile.objects.active(), user)
        if not allowed.filter(pk=value.pk).exists():
            raise serializers.ValidationError(
                "Ushbu nomzodga so'rov yuborish mumkin emas."
            )

        if (
            PhotoRequest.objects.active()
            .filter(
                from_profile=profile,
                to_profile=value,
                status=PhotoRequestStatus.PENDING,
            )
            .exists()
        ):
            raise serializers.ValidationError(
                "Bu nomzodga yuborgan so'rovingiz hali ko'rib chiqilmoqda."
            )

        return value
