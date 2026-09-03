from rest_framework import serializers

from apps.accounts.users.models import User
from apps.core.base.serializers import BaseModelSerializer
from apps.matches.chats.models import Message

from .models import Complaint, ComplaintReason, ComplaintStatus
from .services import build_ai_analysis, build_profile_snapshot


class ComplaintUserShortSerializer(BaseModelSerializer):
    display_id = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "phone_number", "email", "display_id", "full_name", "profile"]
        related_fields = {
            "profile": ["id", "first_name", "last_name"],
        }

    def get_display_id(self, obj):
        short_code = str(obj.id).replace("-", "")[:5].upper()
        return f"USR-{short_code}"

    def get_full_name(self, obj):
        profile = getattr(obj, "profile", None)
        if profile and (profile.first_name or profile.last_name):
            return f"{profile.first_name or ''} {profile.last_name or ''}".strip()
        return obj.phone_number or obj.email or ""


class ComplaintMessageExcerptSerializer(BaseModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "content", "sender", "sender_name", "created_at"]
        related_fields = {
            "sender": ComplaintUserShortSerializer,
        }

    def get_sender_name(self, obj):
        profile = getattr(obj.sender, "profile", None)
        if profile and (profile.first_name or profile.last_name):
            return f"{profile.first_name or ''} {profile.last_name or ''}".strip()
        return obj.sender.phone_number or obj.sender.email or ""


class ComplaintCreateSerializer(BaseModelSerializer):
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "from_user",
            "to_user",
            "chat_room",
            "reason",
            "reason_label",
            "message",
            "evidence",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["from_user", "status"]
        related_fields = {
            "from_user": ComplaintUserShortSerializer,
            "to_user": ComplaintUserShortSerializer,
            "chat_room": ["id"],
        }

    def validate_to_user(self, value):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and value.id == user.id:
            raise serializers.ValidationError("O'zingiz haqingizda shikoyat yubora olmaysiz.")
        return value

    def validate_reason(self, value):
        valid_values = {item.value for item in ComplaintReason}
        if value not in valid_values:
            raise serializers.ValidationError("Shikoyat sababi noto'g'ri tanlangan.")
        return value

    def validate(self, attrs):
        forbidden_fields = {"status", "admin_note", "resolved_by", "resolved_at"}
        sent_forbidden = set(self.initial_data.keys()) & forbidden_fields
        if sent_forbidden:
            field = sorted(sent_forbidden)[0]
            raise serializers.ValidationError(
                {field: "Ushbu maydonni shikoyat yaratishda yuborib bo'lmaydi."}
            )
        return attrs


class ComplaintListSerializer(BaseModelSerializer):
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "from_user",
            "to_user",
            "reason",
            "reason_label",
            "status",
            "status_label",
            "created_at",
        ]
        related_fields = {
            "from_user": ComplaintUserShortSerializer,
            "to_user": ComplaintUserShortSerializer,
        }


class ComplaintMyListSerializer(BaseModelSerializer):
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "to_user",
            "reason",
            "reason_label",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        ]
        related_fields = {
            "to_user": ComplaintUserShortSerializer,
        }


class ComplaintDetailSerializer(BaseModelSerializer):
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    conversation_excerpt = serializers.SerializerMethodField()
    profile_snapshot = serializers.SerializerMethodField()
    ai_analysis = serializers.SerializerMethodField()
    previous_complaints_count = serializers.SerializerMethodField()

    class Meta:
        model = Complaint
        fields = [
            "id",
            "from_user",
            "to_user",
            "chat_room",
            "reason",
            "reason_label",
            "message",
            "evidence",
            "status",
            "status_label",
            "admin_note",
            "resolved_by",
            "resolved_at",
            "conversation_excerpt",
            "profile_snapshot",
            "ai_analysis",
            "previous_complaints_count",
            "created_at",
            "updated_at",
        ]
        related_fields = {
            "from_user": ComplaintUserShortSerializer,
            "to_user": ComplaintUserShortSerializer,
            "resolved_by": ComplaintUserShortSerializer,
            "chat_room": ["id"],
        }

    def get_conversation_excerpt(self, obj):
        chat_room = getattr(obj, "chat_room", None)
        if not chat_room:
            return []

        messages = chat_room.messages.select_related("sender", "sender__profile").order_by(
            "created_at"
        )[:10]
        return ComplaintMessageExcerptSerializer(messages, many=True).data

    def get_profile_snapshot(self, obj):
        return build_profile_snapshot(obj.to_user)

    def get_ai_analysis(self, obj):
        return build_ai_analysis(obj)

    def get_previous_complaints_count(self, obj):
        return Complaint.objects.active().filter(to_user=obj.to_user).exclude(
            pk=obj.pk
        ).count()


class ComplaintUpdateSerializer(BaseModelSerializer):
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "to_user",
            "chat_room",
            "reason",
            "reason_label",
            "message",
            "evidence",
            "admin_note",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "created_at", "updated_at"]
        related_fields = {
            "to_user": ComplaintUserShortSerializer,
            "chat_room": ["id"],
        }

    def validate_reason(self, value):
        valid_values = {item.value for item in ComplaintReason}
        if value not in valid_values:
            raise serializers.ValidationError("Shikoyat sababi noto'g'ri tanlangan.")
        return value

    def validate(self, attrs):
        forbidden_fields = {"from_user", "resolved_by", "resolved_at", "status"}
        sent_forbidden = set(self.initial_data.keys()) & forbidden_fields
        if sent_forbidden:
            field = sorted(sent_forbidden)[0]
            raise serializers.ValidationError(
                {field: "Ushbu maydonni bu endpoint orqali o'zgartirib bo'lmaydi."}
            )

        to_user = attrs.get("to_user", getattr(self.instance, "to_user", None))
        from_user = getattr(self.instance, "from_user", None)
        if to_user and from_user and to_user.id == from_user.id:
            raise serializers.ValidationError(
                {"to_user": "Shikoyat yuboruvchi va qilingan foydalanuvchi bir xil bo'lishi mumkin emas."}
            )
        return attrs


class ComplaintDecisionSerializer(BaseModelSerializer):
    decision = serializers.ChoiceField(
        choices=[
            (ComplaintStatus.APPROVED, "Tasdiqlash"),
            (ComplaintStatus.REJECTED, "Bekor qilish"),
        ],
        write_only=True,
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "decision",
            "status",
            "status_label",
            "admin_note",
            "resolved_by",
            "resolved_at",
            "updated_at",
        ]
        read_only_fields = ["status", "resolved_by", "resolved_at", "updated_at"]
        related_fields = {
            "resolved_by": ComplaintUserShortSerializer,
        }

    def validate(self, attrs):
        if self.instance.status != ComplaintStatus.PENDING:
            raise serializers.ValidationError(
                {"decision": "Hal qilingan shikoyat bo'yicha qayta qaror chiqarib bo'lmaydi."}
            )
        return attrs
