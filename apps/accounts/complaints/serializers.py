from rest_framework import serializers

from apps.accounts.users.models import User
from apps.core.base.serializers import BaseModelSerializer
from apps.matches.chats.models import Message

from .models import (
    Complaint,
    ComplaintEnforcementAction,
    ComplaintReason,
    ComplaintStatus,
)
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
            raise serializers.ValidationError(
                "O'zingiz haqingizda shikoyat yubora olmaysiz."
            )
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
    enforcement_action_label = serializers.CharField(
        source="get_enforcement_action_display", read_only=True
    )
    conversation_excerpt = serializers.SerializerMethodField()
    profile_snapshot = serializers.SerializerMethodField()
    ai_analysis = serializers.SerializerMethodField()
    previous_complaints_count = serializers.SerializerMethodField()
    block_history = serializers.SerializerMethodField()

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
            "enforcement_action",
            "enforcement_action_label",
            "resolved_by",
            "resolved_at",
            "conversation_excerpt",
            "profile_snapshot",
            "ai_analysis",
            "previous_complaints_count",
            "block_history",
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

        messages = chat_room.messages.select_related(
            "sender", "sender__profile"
        ).order_by("created_at")[:10]
        return ComplaintMessageExcerptSerializer(messages, many=True).data

    def get_profile_snapshot(self, obj):
        return build_profile_snapshot(obj.to_user)

    def get_ai_analysis(self, obj):
        return build_ai_analysis(obj)

    def get_previous_complaints_count(self, obj):
        return (
            Complaint.objects.active()
            .filter(to_user=obj.to_user)
            .exclude(pk=obj.pk)
            .count()
        )

    def get_block_history(self, obj):
        """
        Shikoyat qilingan foydalanuvchining bloklanish/blokdan chiqarilish
        tarixi (auditlog orqali, `is_blocked` maydoni o'zgargan har bir yozuv).
        """
        from auditlog.models import LogEntry
        from django.contrib.contenttypes.models import ContentType

        from apps.accounts.users.admin_serializers import _actor_display_name

        events = []
        try:
            ct = ContentType.objects.get_for_model(User)
            block_entries = (
                LogEntry.objects.filter(
                    content_type=ct,
                    object_pk=str(obj.to_user_id),
                    action=LogEntry.Action.UPDATE,
                )
                .filter(changes__has_key="is_blocked")
                .select_related("actor", "actor__profile")
                .order_by("timestamp")
            )
            for entry in block_entries:
                change = entry.changes_dict.get("is_blocked")
                if not change or len(change) < 2 or change[0] == change[1]:
                    continue
                became_blocked = str(change[1]) == "True"
                events.append(
                    {
                        "event_type": "user_blocked"
                        if became_blocked
                        else "user_unblocked",
                        "label": "Bloklandi"
                        if became_blocked
                        else "Blokdan chiqarildi",
                        "actor": _actor_display_name(entry.actor),
                        "date": entry.timestamp,
                    }
                )
        except Exception:
            pass
        return events


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
                {
                    "to_user": "Shikoyat yuboruvchi va qilingan foydalanuvchi bir xil bo'lishi mumkin emas."
                }
            )
        return attrs


class ComplaintDecisionSerializer(BaseModelSerializer):
    decision = serializers.ChoiceField(
        choices=[
            (ComplaintStatus.APPROVED, "Tasdiqlash"),
            (ComplaintStatus.REJECTED, "Bekor qilish"),
        ],
        write_only=True,
        help_text="Qaror turi: 'approved' — tasdiqlash, 'rejected' — bekor qilish.",
    )
    enforcement_action = serializers.ChoiceField(
        choices=ComplaintEnforcementAction.choices,
        required=False,
        allow_null=True,
        write_only=True,
        help_text=(
            "decision='approved' bo'lganda majburiy. 'warn' — ogohlantirish "
            "yuborish (profil ochiq qoladi), 'block' — profilni bloklash "
            "(foydalanuvchi tizimga kira olmaydi)."
        ),
    )
    admin_note = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text=(
            "decision='rejected' bo'lganda majburiy (10-500 belgi) — bekor "
            "qilish sababi. decision='approved' bo'lganda ixtiyoriy."
        ),
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    enforcement_action_label = serializers.CharField(
        source="get_enforcement_action_display", read_only=True
    )

    class Meta:
        model = Complaint
        fields = [
            "id",
            "decision",
            "enforcement_action",
            "enforcement_action_label",
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
        """
        Qaror qabul qilish shartlarini tekshiradi: hal qilingan shikoyatga
        qayta qaror chiqarib bo'lmaydi; tasdiqlashda chora tanlash majburiy;
        rad etishda sabab majburiy va uzunligi 10-500 belgi oralig'ida bo'lishi kerak.
        """
        if self.instance.status != ComplaintStatus.PENDING:
            raise serializers.ValidationError(
                {
                    "decision": "Hal qilingan shikoyat bo'yicha qayta qaror chiqarib bo'lmaydi."
                }
            )

        decision = attrs.get("decision")
        admin_note = (attrs.get("admin_note") or "").strip()

        if decision == ComplaintStatus.REJECTED:
            if not admin_note:
                raise serializers.ValidationError(
                    {"admin_note": "Bekor qilish sababi majburiy."}
                )
            if len(admin_note) < 10:
                raise serializers.ValidationError(
                    {"admin_note": "Kamida 10 ta belgi bo'lishi kerak."}
                )
            if len(admin_note) > 500:
                raise serializers.ValidationError(
                    {"admin_note": "Ko'pi bilan 500 ta belgi bo'lishi mumkin."}
                )

        if decision == ComplaintStatus.APPROVED and not attrs.get("enforcement_action"):
            raise serializers.ValidationError(
                {"enforcement_action": "Majburiy maydon."}
            )

        return attrs
