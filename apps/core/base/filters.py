import django_filters

class UUIDInFilter(django_filters.BaseInFilter, django_filters.UUIDFilter):

    pass

class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):

    pass

class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):

    pass
