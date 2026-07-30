from rest_framework import serializers

class BaseModelSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "is_active" in self.fields:
            self.fields.pop("is_active")

        readonly_fields = ["id", "created_at", "updated_at"]
        for field_name in readonly_fields:
            if field_name in self.fields:
                self.fields[field_name].read_only = True

        related_fields = getattr(self.Meta, "related_fields", [])

        if isinstance(related_fields, dict):
            items = related_fields.items()
        else:
            items = [(f, None) for f in related_fields]

        for field_name, val in items:
            source = field_name
            fields_to_serialize = val
            nested_related = {}

            if isinstance(val, dict):
                source = val.get("source", field_name).replace("__", ".")
                fields_to_serialize = val.get("fields", "__all__")
                nested_related = val.get("related_fields", {})

            if field_name in self.fields:
                self.fields[field_name].write_only = True

            is_many = False
            related_model = None
            try:
                curr_model = self.Meta.model
                field = None
                for part in source.split("."):
                    field = curr_model._meta.get_field(part)
                    curr_model = field.related_model

                if field:
                    is_many = getattr(field, "many_to_many", False) or getattr(
                        field, "one_to_many", False
                    )
                related_model = curr_model
            except Exception:
                pass

            if isinstance(fields_to_serialize, type) and issubclass(
                fields_to_serialize, serializers.Serializer
            ):
                serializer_class = fields_to_serialize
            else:
                if not related_model:
                    continue
                serializer_class = get_short_serializer(
                    related_model,
                    fields=fields_to_serialize,
                    nested_related_fields=nested_related,
                )

            self.fields[f"{field_name}_info"] = serializer_class(
                source=source, read_only=True, many=is_many
            )

        view = self.context.get("view")
        if view and hasattr(view, "serializer_fields") and view.serializer_fields:
            allowed = set(view.serializer_fields)

            for f in view.serializer_fields:
                allowed.add(f"{f}_info")

            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "created_at" in ret:
            val = ret.pop("created_at")
            ret["created_at"] = val
        if "updated_at" in ret:
            val = ret.pop("updated_at")
            ret["updated_at"] = val
        return ret

def get_short_serializer(model_class, fields=None, nested_related_fields=None):

    _fields = fields or "__all__"
    _related_fields = nested_related_fields or {}

    class DynamicShortSerializer(BaseModelSerializer):
        class Meta:
            model = model_class
            fields = _fields
            related_fields = _related_fields

    DynamicShortSerializer.__name__ = f"{model_class.__name__}ShortSerializer"
    return DynamicShortSerializer
