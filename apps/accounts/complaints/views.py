from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.core.base.permissions import FullDjangoModelPermissions
from apps.core.base.views import BaseManageViewSet

from .filters import ComplaintFilter
from .models import Complaint, ComplaintEnforcementAction, ComplaintStatus
from .serializers import (
    ComplaintCreateSerializer,
    ComplaintDecisionSerializer,
    ComplaintDetailSerializer,
    ComplaintListSerializer,
    ComplaintMyListSerializer,
    ComplaintUpdateSerializer,
)
from .services import apply_complaint_enforcement, is_staff_like


class ComplaintViewSet(BaseManageViewSet):
    queryset = Complaint.objects.active()
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ComplaintFilter
    search_fields = [
        "from_user__phone_number",
        "to_user__phone_number",
        "from_user__profile__first_name",
        "from_user__profile__last_name",
        "to_user__profile__first_name",
        "to_user__profile__last_name",
        "message",
    ]
    ordering_fields = ["created_at", "resolved_at"]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        if self.action in ("decision", "unblock"):
            return [permissions.IsAuthenticated()]
        if self.action == "my":
            return [permissions.IsAuthenticated()]
        return [FullDjangoModelPermissions()]

    def get_queryset(self):
        qs = Complaint.objects.select_related(
            "from_user",
            "from_user__profile",
            "to_user",
            "to_user__profile",
            "resolved_by",
            "resolved_by__profile",
            "chat_room",
        ).active()

        if self.action in ["retrieve", "decision", "unblock"]:
            qs = qs.prefetch_related("chat_room__messages__sender__profile")

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return ComplaintCreateSerializer
        if self.action == "list":
            return ComplaintListSerializer
        if self.action == "retrieve":
            return ComplaintDetailSerializer
        if self.action == "update":
            return ComplaintUpdateSerializer
        if self.action == "partial_update":
            return ComplaintUpdateSerializer
        if self.action == "decision":
            return ComplaintDecisionSerializer
        if self.action == "my":
            return ComplaintMyListSerializer
        return ComplaintDetailSerializer

    @extend_schema(summary="Foydalanuvchilar o'rtasidagi shikoyatni yaratish")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="Shikoyatlar ro'yxatini olish")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Shikoyat tafsilotini olish")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary="Shikoyat ma'lumotlarini to'liq yangilash")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(summary="Shikoyat ma'lumotlarini qisman yangilash")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Shikoyat bo'yicha admin qarorini saqlash",
        description=(
            "decision='approved' bo'lsa enforcement_action majburiy "
            "(warn/block). decision='rejected' bo'lsa admin_note majburiy "
            "(10-500 belgi)."
        ),
        request=ComplaintDecisionSerializer,
        responses={200: ComplaintDecisionSerializer},
        examples=[
            OpenApiExample(
                "Tasdiqlash — ogohlantirish",
                value={"decision": "approved", "enforcement_action": "warn"},
                request_only=True,
            ),
            OpenApiExample(
                "Tasdiqlash — bloklash",
                value={
                    "decision": "approved",
                    "enforcement_action": "block",
                    "admin_note": "Takroriy firibgarlik aniqlandi.",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Bekor qilish",
                value={
                    "decision": "rejected",
                    "admin_note": "Dalillar yetarli emas, skrinshot boshqa foydalanuvchiga tegishli.",
                },
                request_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="decision")
    def decision(self, request, pk=None):
        if not is_staff_like(request.user):
            return Response(
                {
                    "detail": "Sizda ushbu shikoyat bo'yicha qaror chiqarish huquqi yo'q."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        complaint = self.get_object()
        serializer = self.get_serializer(complaint, data=request.data)
        serializer.is_valid(raise_exception=True)

        decision = serializer.validated_data["decision"]
        enforcement_action = (
            serializer.validated_data.get("enforcement_action")
            if decision == ComplaintStatus.APPROVED
            else None
        )

        with transaction.atomic():
            complaint.status = decision
            complaint.admin_note = serializer.validated_data.get("admin_note")
            complaint.enforcement_action = enforcement_action
            complaint.resolved_by = request.user
            complaint.resolved_at = timezone.now()
            complaint.save(
                update_fields=[
                    "status",
                    "admin_note",
                    "enforcement_action",
                    "resolved_by",
                    "resolved_at",
                    "updated_at",
                ]
            )

            if decision == ComplaintStatus.APPROVED:
                apply_complaint_enforcement(complaint, enforcement_action)

        response_serializer = self.get_serializer(complaint)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Shikoyat orqali bloklangan foydalanuvchini blokdan chiqarish",
        description=(
            "Faqat shu shikoyat asosida (enforcement_action='block') hozir "
            "bloklangan foydalanuvchi uchun ishlaydi. Sabab talab qilinmaydi — "
            "kontekst shikoyatning o'zidan ma'lum."
        ),
        request=None,
        responses={200: ComplaintDetailSerializer},
    )
    @action(detail=True, methods=["post"], url_path="unblock")
    def unblock(self, request, pk=None):
        if not is_staff_like(request.user):
            return Response(
                {"detail": "Sizda ushbu amalni bajarish huquqi yo'q."},
                status=status.HTTP_403_FORBIDDEN,
            )

        complaint = self.get_object()

        if (
            complaint.status != ComplaintStatus.APPROVED
            or complaint.enforcement_action != ComplaintEnforcementAction.BLOCK
        ):
            return Response(
                {"detail": "Bu shikoyat orqali hech kim bloklanmagan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        to_user = complaint.to_user
        if not to_user.is_blocked:
            return Response(
                {"detail": "Foydalanuvchi allaqachon blokdan chiqarilgan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.accounts.users.services import unblock_user

        unblock_user(
            to_user,
            reason=f"Shikoyat (#{complaint.id}) bo'yicha bloklash bekor qilindi",
            notify_user=bool(request.data.get("notify_user", False)),
        )

        response_serializer = self.get_serializer(complaint)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(summary="Foydalanuvchining o'z shikoyatlarini olish")
    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        queryset = (
            self.filter_queryset(self.get_queryset())
            .filter(from_user=request.user)
            .order_by("-created_at")
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save(from_user=self.request.user, status=ComplaintStatus.PENDING)
