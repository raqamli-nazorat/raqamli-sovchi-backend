from rest_framework import viewsets
from apps.core.base.mixins import (
    DynamicPermissionMixin,
    AutoSchemaMixin,
)


class BaseManageViewSet(AutoSchemaMixin, DynamicPermissionMixin, viewsets.ModelViewSet):
    """
    CRUD amallari uchun bazaviy ViewSet.
    """

    pass


class BaseReadOnlyViewSet(
    AutoSchemaMixin, DynamicPermissionMixin, viewsets.ReadOnlyModelViewSet
):
    """
    Faqat o'qish amallari (List, Retrieve) uchun mo'ljallangan bazaviy ViewSet.
    """

    pass
