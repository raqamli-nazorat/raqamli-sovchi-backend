from apps.core.base.serializers import BaseModelSerializer
from .models import MatchRequest


class MatchRequestSerializer(BaseModelSerializer):
    class Meta:
        model = MatchRequest
        fields = "__all__"
        related_fields = {
            "from_profile": ["id", "first_name", "last_name"],
            "to_profile": ["id", "first_name", "last_name"],
            "question": ["id", "order", "text"],
        }
