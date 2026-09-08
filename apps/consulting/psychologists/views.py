from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.base.views import BaseManageViewSet

from .filters import PsychologistFilter
from .models import Psychologist
from .serializers import PsychologistSerializer


class PsychologistViewSet(BaseManageViewSet):
    """Psixologlarni boshqarish (boshqaruv paneli uchun).

    Faol/nofaol holat `PATCH {"is_available": bool}` orqali o'zgartiriladi.
    O'chirish — yumshoq (`is_active=False`).
    """

    queryset = Psychologist.objects.active()
    serializer_class = PsychologistSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PsychologistFilter
    search_fields = ["first_name", "last_name", "phone_number", "specialization"]
    ordering_fields = ["created_at", "experience_years", "price"]
    ordering = ["-created_at"]
