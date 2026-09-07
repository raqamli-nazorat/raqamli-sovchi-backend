from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.users.permissions import IsStaffMember
from apps.core.base.mixins import AutoSchemaMixin
from apps.core.utils.throttles import CustomScopedRateThrottle

from .serializers import DashboardSummarySerializer
from .services import get_dashboard_summary

DEFAULT_DAYS = 14
MIN_DAYS = 1
MAX_DAYS = 90
CACHE_TTL = 300


class DashboardSummaryView(AutoSchemaMixin, APIView):
    """Boshqaruv paneli uchun umumlashgan statistika — bitta soʻrov."""

    permission_classes = [IsStaffMember]
    throttle_classes = [CustomScopedRateThrottle]
    throttle_scope = "dashboard"
    serializer_class = DashboardSummarySerializer

    def _get_days(self, request):
        """`days` query parametrini tekshirib butun songa aylantiradi."""
        raw = request.query_params.get("days")
        if raw is None:
            return DEFAULT_DAYS
        try:
            days = int(raw)
        except (TypeError, ValueError):
            raise ValidationError({"days": "days butun son boʻlishi kerak."})
        if days < MIN_DAYS or days > MAX_DAYS:
            raise ValidationError(
                {"days": f"days {MIN_DAYS} dan {MAX_DAYS} gacha boʻlishi kerak."}
            )
        return days

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="days",
                type=int,
                description=(
                    f"Dinamika oraligʻi (kunlarda). Default {DEFAULT_DAYS}, "
                    f"{MIN_DAYS}–{MAX_DAYS} oraligʻida."
                ),
            )
        ],
        responses=DashboardSummarySerializer,
    )
    def get(self, request, *args, **kwargs):
        """Barcha koʻrsatkichlarni qaytaradi (natija 5 daqiqa keshlanadi)."""
        days = self._get_days(request)
        cache_key = f"dashboard:summary:{days}"
        data = cache.get(cache_key)
        if data is None:
            data = get_dashboard_summary(days)
            cache.set(cache_key, data, CACHE_TTL)
        return Response(data)
