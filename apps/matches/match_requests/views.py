from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.base.views import BaseManageViewSet
from apps.core.utils.throttles import CustomScopedRateThrottle
from .models import MatchRequest, MatchRequestStatus, VisibilityScope
from .serializers import MatchRequestSerializer
from .services import (
    can_decide_match_request,
    filter_match_requests_for_user,
    get_representative_user,
)


class MatchRequestViewSet(BaseManageViewSet):
    serializer_class = MatchRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "from_profile", "to_profile"]
    search_fields = ["note"]
    ordering_fields = ["created_at"]

    def get_throttles(self):
        """
        So'rov yuborish (create) uchun alohida, qattiqroq cheklov qo'llaydi.

        Qolgan amallar umumiy cheklov ostida qoladi.

        :return: Throttle obyektlari ro'yxati.
        """
        if self.action == "create":
            self.throttle_scope = "match_request"
            return [CustomScopedRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        qs = MatchRequest.objects.select_related(
            "from_profile", "to_profile", "question"
        ).active()
        return filter_match_requests_for_user(qs, self.request.user)

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
                    "type": "match_request_created",
                    "request_id": str(instance.id),
                    "from_profile_id": str(instance.from_profile_id),
                },
            )

    @staticmethod
    def _ensure_undecided(match_req):
        """
        So'rov allaqachon hal qilinganini tekshiradi.

        Qabul qilingan yoki rad etilgan so'rovni qayta hal qilishga yo'l qo'ymaydi:
        aks holda holat orqaga qaytariladi va har safar yangi xabarnoma yuboriladi.

        :param match_req: Moslik so'rovi (MatchRequest).
        :return: None
        :raises ValidationError: So'rov allaqachon hal qilingan bo'lsa.
        """
        decided = (MatchRequestStatus.ACCEPTED, MatchRequestStatus.REJECTED)
        if match_req.status in decided:
            raise ValidationError(
                f"Bu so'rov allaqachon hal qilingan ({match_req.get_status_display()})."
            )

    @action(detail=True, methods=["post"], url_path="accept")
    def accept_request(self, request, pk=None):
        match_req = self.get_object()

        if not can_decide_match_request(request.user, match_req):
            return Response(
                {"detail": "Sizda ushbu so'rovni qabul qilish huquqi yo'q."},
                status=status.HTTP_403_FORBIDDEN,
            )

        self._ensure_undecided(match_req)

        visibility_scope = request.data.get(
            "visibility_scope", VisibilityScope.ONLY_THIS_USER
        )
        if visibility_scope not in VisibilityScope.values:
            raise ValidationError(
                {
                    "visibility_scope": "Noto'g'ri qiymat. Ruxsat etilganlari: "
                    f"{', '.join(VisibilityScope.values)}."
                }
            )

        from apps.accounts.notifications.models import Notification

        if visibility_scope == VisibilityScope.FORWARD_TO_REPRESENTATIVE:
            match_req.status = MatchRequestStatus.FORWARDED_TO_REPRESENTATIVE
            match_req.visibility_scope = VisibilityScope.FORWARD_TO_REPRESENTATIVE
            match_req.save(update_fields=["status", "visibility_scope", "updated_at"])

            representative_user = get_representative_user(match_req.to_profile)
            if representative_user:
                Notification.objects.create(
                    user=representative_user,
                    title="Vakilga yo'naltirilgan rasm so'rovi",
                    message=f"{match_req.to_profile.first_name} rasm so'rovini sizga hal qilish uchun yo'naltirdi.",
                    extra_data={
                        "type": "match_request_forwarded",
                        "request_id": str(match_req.id),
                    },
                )

            return Response(
                {
                    "message": "So'rov vakilingizga hal qilish uchun yo'naltirildi.",
                    "status": match_req.status,
                    "visibility_scope": match_req.visibility_scope,
                },
                status=status.HTTP_200_OK,
            )

        match_req.status = MatchRequestStatus.ACCEPTED
        match_req.visibility_scope = VisibilityScope.ONLY_THIS_USER
        match_req.save(update_fields=["status", "visibility_scope", "updated_at"])

        from apps.matches.chats.models import ChatRoom

        chat_room, _ = ChatRoom.objects.get_or_create(match_request=match_req)

        if match_req.from_profile and match_req.from_profile.user:
            receiver_name = (
                match_req.to_profile.first_name
                if match_req.to_profile
                else "Foydalanuvchi"
            )
            Notification.objects.create(
                user=match_req.from_profile.user,
                title="Rasm ko'rish so'rovi qabul qilindi!",
                message=f"{receiver_name} rasm ko'rish so'rovingizni qabul qildi.",
                extra_data={
                    "type": "match_request_accepted",
                    "request_id": str(match_req.id),
                    "chat_room_id": str(chat_room.id),
                },
            )

        return Response(
            {
                "message": "Moslik so'rovi qabul qilindi. Rasm ushbu nomzod uchun ochildi va chat xonasi yaratildi.",
                "chat_room_id": str(chat_room.id),
                "status": match_req.status,
                "visibility_scope": match_req.visibility_scope,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject_request(self, request, pk=None):
        match_req = self.get_object()

        if not can_decide_match_request(request.user, match_req):
            return Response(
                {"detail": "Sizda ushbu so'rovni rad etish huquqi yo'q."},
                status=status.HTTP_403_FORBIDDEN,
            )

        self._ensure_undecided(match_req)

        match_req.status = MatchRequestStatus.REJECTED
        match_req.save(update_fields=["status", "updated_at"])

        if match_req.from_profile and match_req.from_profile.user:
            from apps.accounts.notifications.models import Notification

            receiver_name = (
                match_req.to_profile.first_name
                if match_req.to_profile
                else "Foydalanuvchi"
            )
            Notification.objects.create(
                user=match_req.from_profile.user,
                title="Rasm ko'rish so'rovi rad etildi",
                message=f"{receiver_name} rasm ko'rish so'rovingizni rad etdi.",
                extra_data={
                    "type": "match_request_rejected",
                    "request_id": str(match_req.id),
                },
            )

        return Response(
            {
                "message": "Moslik so'rovi rad etildi.",
                "status": match_req.status,
            },
            status=status.HTTP_200_OK,
        )
