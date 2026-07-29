from django.utils import timezone
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.users.models import User, AuthProvider
from apps.accounts.users.serializers import UserSerializer
from .models import LoginCode
from .serializers import VerifyCodeSerializer


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class VerifyCodeView(views.APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]
        code = serializer.validated_data["code"]

        login_code = (
            LoginCode.objects
            .filter(phone_number=phone_number, code=code, is_used=False)
            .filter(expires_at__gt=timezone.now())
            .order_by("-created_at")
            .first()
        )

        if not login_code:
            raise ValidationError("Kod noto'g'ri yoki muddati o'tgan.")

        login_code.is_used = True
        login_code.save(update_fields=["is_used"])

        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={"auth_provider": AuthProvider.TELEGRAM},
        )

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": tokens,
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
