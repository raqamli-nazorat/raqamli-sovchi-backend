import django_filters

from .models import Psychologist


class PsychologistFilter(django_filters.FilterSet):
    specialization = django_filters.CharFilter(lookup_expr="icontains")
    experience_min = django_filters.NumberFilter(
        field_name="experience_years", lookup_expr="gte"
    )
    experience_max = django_filters.NumberFilter(
        field_name="experience_years", lookup_expr="lte"
    )
    price_min = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Psychologist
        fields = ["is_available", "specialization"]
