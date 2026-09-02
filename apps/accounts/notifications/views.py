import uuid

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.base.mixins import AutoSchemaMixin

from .models import Notification, UserDevice
from .serializers import (
    NotificationSerializer,
    UserDeviceRegisterSerializer,
    UserDeviceUnregisterSerializer,
)


class WebSocketTicketView(AutoSchemaMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ticket = str(uuid.uuid4())
        cache.set(f"ws_ticket_{ticket}", request.user.id, timeout=60)

        return Response({"ticket": ticket, "expires_in": 60})


class NotificationListView(AutoSchemaMixin, generics.ListAPIView):
    queryset = Notification.objects.active()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_read"]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class NotificationCountView(AutoSchemaMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        counts = Notification.objects.filter(
            user=request.user, is_active=True
        ).aggregate(
            unread_count=Count("id", filter=Q(is_read=False)),
            read_count=Count("id", filter=Q(is_read=True)),
            total_count=Count("id"),
        )

        return Response(
            {
                "unread": counts["unread_count"],
                "read": counts["read_count"],
                "total": counts["total_count"],
            }
        )


class MarkNotificationReadView(AutoSchemaMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        update_rows = Notification.objects.filter(
            pk=pk, user=self.request.user, is_read=False
        ).update(is_read=True)

        if update_rows:
            return Response(
                {"message": "Xabar o'qildi deb belgilandi."}, status=status.HTTP_200_OK
            )

        return Response(
            {"detail": "Xabar topilmadi yoki allaqachon o'qilgan."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class MarkAllNotificationsAsReadView(AutoSchemaMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)

        return Response(
            {
                "message": f"{updated_count} ta xabar muvaffaqiyatli o'qildi.",
            }
        )


class UserDeviceRegisterView(AutoSchemaMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserDeviceRegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = UserDeviceRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["fcm_token"]
        device_id = serializer.validated_data["device_id"]
        device_type = serializer.validated_data["device_type"]

        try:
            with transaction.atomic():
                UserDevice.objects.filter(fcm_token=token).exclude(
                    device_id=device_id
                ).delete()

                device, created = UserDevice.objects.update_or_create(
                    device_id=device_id,
                    defaults={
                        "user": request.user,
                        "fcm_token": token,
                        "device_type": device_type,
                        "is_active": True,
                    },
                )
        except IntegrityError:
            created = False

        return Response(
            {
                "message": "Qurilma muvaffaqiyatli ro'yxatdan o'tdi",
                "status": "created" if created else "updated",
            },
            status=status.HTTP_200_OK,
        )


class UserDeviceUnregisterView(AutoSchemaMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserDeviceUnregisterSerializer

    def delete(self, request, *args, **kwargs):
        device_id = request.data.get("device_id") or request.query_params.get(
            "device_id"
        )
        if device_id:
            UserDevice.objects.filter(user=request.user, device_id=device_id).delete()
        else:
            UserDevice.objects.filter(user=request.user).delete()

        return Response(
            {"message": "Qurilma muvaffaqiyatli ro'yxatdan chiqarildi."},
            status=status.HTTP_200_OK,
        )
