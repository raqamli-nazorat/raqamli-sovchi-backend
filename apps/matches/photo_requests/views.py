from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.core.base.views import BaseManageViewSet
from apps.core.utils.throttles import CustomScopedRateThrottle

from .models import PhotoRequest, PhotoRequestStatus
from .serializers import PhotoRequestSerializer
from .services import can_decide_photo_request, filter_photo_requests_for_user


class PhotoRequestViewSet(BaseManageViewSet):
    serializer_class = PhotoRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "from_profile", "to_profile"]
    ordering_fields = ["created_at"]

    def get_throttles(self):
        """
        So'rov yuborish (create) uchun alohida, qattiqroq cheklov qo'llaydi.

        Qolgan amallar umumiy cheklov ostida qoladi.

        :return: Throttle obyektlari ro'yxati.
        """
        if self.action == "create":
            self.throttle_scope = "photo_request"
            return [CustomScopedRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        qs = PhotoRequest.objects.select_related("from_profile", "to_profile").active()
        return filter_photo_requests_for_user(qs, self.request.user)

    def perform_create(self, serializer):
        user_profile = getattr(self.request.user, "profile", None)
        if not user_profile:
            raise ValidationError(
                "So'rov yuborish uchun avval o'z anketangizni to'ldirishingiz kerak."
            )

        instance = serializer.save(from_profile=user_profile)

        if instance.to_profile and instance.to_profile.user:
            from apps.accounts.notifications.models import Notification

            sender_name = user_profile.first_name if user_profile else "Foydalanuvchi"
            note_str = f" Izoh: «{instance.note}»" if instance.note else ""
            Notification.objects.create(
                user=instance.to_profile.user,
                title="Yangi rasm ko'rish so'rovi",
                message=f"{sender_name} sizga rasm ko'rish so'rovini yubordi.{note_str}",
                extra_data={
                    "type": "photo_request_created",
                    "request_id": str(instance.id),
                    "from_profile_id": str(instance.from_profile_id),
                },
            )

    @staticmethod
    def _ensure_undecided(photo_req):
        """
        So'rov allaqachon hal qilinganini tekshiradi.

        Qabul qilingan yoki rad etilgan so'rovni qayta hal qilishga yo'l qo'ymaydi.

        :param photo_req: Rasm ko'rish so'rovi (PhotoRequest).
        :raises ValidationError: So'rov allaqachon hal qilingan bo'lsa.
        """
        decided = (PhotoRequestStatus.ACCEPTED, PhotoRequestStatus.REJECTED)
        if photo_req.status in decided:
            raise ValidationError(
                f"Bu so'rov allaqachon hal qilingan ({photo_req.get_status_display()})."
            )

    @action(detail=True, methods=["post"], url_path="accept")
    def accept_request(self, request, pk=None):
        """Rasm ko'rish so'rovini qabul qiladi."""
        photo_req = self.get_object()

        if not can_decide_photo_request(request.user, photo_req):
            return Response(
                {"detail": "Sizda ushbu so'rovni qabul qilish huquqi yo'q."},
                status=status.HTTP_403_FORBIDDEN,
            )

        self._ensure_undecided(photo_req)

        photo_req.status = PhotoRequestStatus.ACCEPTED
        photo_req.save(update_fields=["status", "updated_at"])

        if photo_req.from_profile and photo_req.from_profile.user:
            from apps.accounts.notifications.models import Notification

            receiver_name = (
                photo_req.to_profile.first_name
                if photo_req.to_profile
                else "Foydalanuvchi"
            )
            Notification.objects.create(
                user=photo_req.from_profile.user,
                title="Rasm ko'rish so'rovi qabul qilindi!",
                message=f"{receiver_name} rasm ko'rish so'rovingizni qabul qildi.",
                extra_data={
                    "type": "photo_request_accepted",
                    "request_id": str(photo_req.id),
                },
            )

        return Response(
            {
                "message": "Rasm ko'rish so'rovi qabul qilindi.",
                "status": photo_req.status,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject_request(self, request, pk=None):
        """Rasm ko'rish so'rovini rad etadi."""
        photo_req = self.get_object()

        if not can_decide_photo_request(request.user, photo_req):
            return Response(
                {"detail": "Sizda ushbu so'rovni rad etish huquqi yo'q."},
                status=status.HTTP_403_FORBIDDEN,
            )

        self._ensure_undecided(photo_req)

        photo_req.status = PhotoRequestStatus.REJECTED
        photo_req.save(update_fields=["status", "updated_at"])

        if photo_req.from_profile and photo_req.from_profile.user:
            from apps.accounts.notifications.models import Notification

            receiver_name = (
                photo_req.to_profile.first_name
                if photo_req.to_profile
                else "Foydalanuvchi"
            )
            Notification.objects.create(
                user=photo_req.from_profile.user,
                title="Rasm ko'rish so'rovi rad etildi",
                message=f"{receiver_name} rasm ko'rish so'rovingizni rad etdi.",
                extra_data={
                    "type": "photo_request_rejected",
                    "request_id": str(photo_req.id),
                },
            )

        return Response(
            {
                "message": "Rasm ko'rish so'rovi rad etildi.",
                "status": photo_req.status,
            },
            status=status.HTTP_200_OK,
        )
