from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.base.views import BaseManageViewSet
from .models import MatchRequest, MatchRequestStatus, VisibilityScope
from .serializers import MatchRequestSerializer


class MatchRequestViewSet(BaseManageViewSet):
    queryset = MatchRequest.objects.select_related(
        "from_profile", "to_profile", "question"
    ).active()
    serializer_class = MatchRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "from_profile", "to_profile"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        user_profile = getattr(self.request.user, "profile", None)
        if user_profile and not serializer.validated_data.get("from_profile"):
            instance = serializer.save(from_profile=user_profile)
        else:
            instance = serializer.save()

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

    @action(detail=True, methods=["post"], url_path="accept")
    def accept_request(self, request, pk=None):
        match_req = self.get_object()
        user_profile = getattr(request.user, "profile", None)

        if not request.user.is_staff and user_profile != match_req.to_profile:
            return Response(
                {"detail": "Sizda ushbu so'rovni qabul qilish huquqi yo'q."},
                status=status.HTTP_403_FORBIDDEN,
            )

        visibility_scope = request.data.get("visibility_scope", "only_this_user")

        from apps.accounts.notifications.models import Notification

        if visibility_scope == "forward_to_representative":
            match_req.status = MatchRequestStatus.FORWARDED_TO_REPRESENTATIVE
            match_req.visibility_scope = VisibilityScope.FORWARD_TO_REPRESENTATIVE
            match_req.save(update_fields=["status", "visibility_scope", "updated_at"])

            rep_info = getattr(match_req.to_profile, "representative_info", None)
            if rep_info and rep_info.profile and rep_info.profile.user:
                Notification.objects.create(
                    user=rep_info.profile.user,
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
        user_profile = getattr(request.user, "profile", None)

        if not request.user.is_staff and user_profile != match_req.to_profile:
            return Response(
                {"detail": "Sizda ushbu so'rovni rad etish huquqi yo'q."},
                status=status.HTTP_403_FORBIDDEN,
            )

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
