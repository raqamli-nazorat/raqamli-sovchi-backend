from drf_spectacular.utils import extend_schema
from django.utils import timezone
from rest_framework import status, views
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.core.base.mixins import AutoSchemaMixin
from apps.accounts.users.serializers import UserSerializer
from .models import TelegramAuthSession, SessionStatus
from .serializers import TelegramAuthSessionSerializer


class CreateAuthSessionView(AutoSchemaMixin, views.APIView):
    permission_classes = []
    serializer_class = TelegramAuthSessionSerializer

    @extend_schema(request=None, responses={201: TelegramAuthSessionSerializer})
    def post(self, request, *args, **kwargs):
        session = TelegramAuthSession.objects.create()
        serializer = TelegramAuthSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CheckAuthSessionStatusView(AutoSchemaMixin, views.APIView):
    permission_classes = []
    serializer_class = TelegramAuthSessionSerializer

    def get(self, request, session_id, *args, **kwargs):
        session = TelegramAuthSession.objects.filter(session_id=session_id).first()
        if not session:
            raise NotFound("Sessiya topilmadi.")

        if (
            session.status == SessionStatus.PENDING
            and timezone.now() >= session.expires_at
        ):
            session.status = SessionStatus.EXPIRED
            session.save(update_fields=["status"])

        if session.status == SessionStatus.AUTHENTICATED:
            return Response(
                {
                    "status": session.status,
                    "user": UserSerializer(session.user).data if session.user else None,
                    "tokens": {
                        "access": session.access_token,
                        "refresh": session.refresh_token,
                    },
                },
                status=status.HTTP_200_OK,
            )

        return Response({"status": session.status}, status=status.HTTP_200_OK)
