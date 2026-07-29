import django_filters


class UUIDInFilter(django_filters.BaseInFilter, django_filters.UUIDFilter):
    """
    Vergul bilan ajratilgan bir nechta UUID larni qabul qiluvchi (IN lookup) filtr.
    Frontend dan ?field=uuid1,uuid2 kabi so'rovlarni ishlash uchun ishlatiladi.
    """

    pass


class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    """
    Vergul bilan ajratilgan bir nechta raqamlarni (ID) qabul qiluvchi filtr.
    """

    pass


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    """
    Vergul bilan ajratilgan bir nechta matnlarni qabul qiluvchi (IN lookup) filtr.
    """

    pass
