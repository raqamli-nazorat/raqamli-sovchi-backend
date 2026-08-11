from drf_spectacular.utils import extend_schema
from apps.core.base.permissions import FullDjangoModelPermissions


class DynamicPermissionMixin:
    permission_classes = [FullDjangoModelPermissions]


class AutoSchemaMixin:

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        tag_name = None

        is_viewset = False
        if cls.__name__.endswith("ViewSet"):
            is_viewset = True
        elif hasattr(cls, "get_view_name") and "ViewSet" in cls.__name__:
            is_viewset = True

        if is_viewset:
            queryset = getattr(cls, "queryset", None)
            if queryset is not None:
                tag_name = queryset.model.__name__
            elif hasattr(cls, "get_queryset") and callable(cls.get_queryset):
                try:
                    dummy_instance = cls()
                    qs = dummy_instance.get_queryset()
                    if hasattr(qs, "model"):
                        tag_name = qs.model.__name__
                except Exception:
                    pass

            if (
                not tag_name
                and hasattr(cls, "serializer_class")
                and cls.serializer_class
            ):
                meta = getattr(cls.serializer_class, "Meta", None)
                if meta and hasattr(meta, "model"):
                    tag_name = meta.model.__name__
            if not tag_name:
                tag_name = cls.__name__.replace("ViewSet", "")
        else:
            module_parts = cls.__module__.split(".")
            if len(module_parts) >= 3 and module_parts[0] == "apps":
                main_app = module_parts[1].capitalize()
                sub_app = module_parts[2].capitalize()
                tag_name = f"{main_app} ({sub_app})"
            else:
                tag_name = cls.__name__
                for suffix in ["APIView", "View"]:
                    if tag_name.endswith(suffix):
                        tag_name = tag_name[: -len(suffix)]
                        break

        if tag_name:
            extend_schema(tags=[tag_name])(cls)
