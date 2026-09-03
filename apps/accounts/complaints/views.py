from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.core.base.permissions import FullDjangoModelPermissions
from apps.core.base.views import BaseManageViewSet

from .filters import ComplaintFilter
from .models import Complaint, ComplaintStatus
from .serializers import (
    ComplaintCreateSerializer,
    ComplaintDecisionSerializer,
    ComplaintDetailSerializer,
    ComplaintListSerializer,
    ComplaintMyListSerializer,
    ComplaintUpdateSerializer,
)
from .services import is_staff_like


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
        if self.action == "decision":
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

        if self.action in ["retrieve", "decision"]:
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
        request=ComplaintDecisionSerializer,
        responses={200: ComplaintDecisionSerializer},
    )
    @action(detail=True, methods=["post"], url_path="decision")
    def decision(self, request, pk=None):
        if not is_staff_like(request.user):
            return Response(
                {"detail": "Sizda ushbu shikoyat bo'yicha qaror chiqarish huquqi yo'q."},
                status=status.HTTP_403_FORBIDDEN,
            )

        complaint = self.get_object()
        serializer = self.get_serializer(complaint, data=request.data)
        serializer.is_valid(raise_exception=True)

        complaint.status = serializer.validated_data["decision"]
        complaint.admin_note = serializer.validated_data.get("admin_note")
        complaint.resolved_by = request.user
        complaint.resolved_at = timezone.now()
        complaint.save(
            update_fields=[
                "status",
                "admin_note",
                "resolved_by",
                "resolved_at",
                "updated_at",
            ]
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
