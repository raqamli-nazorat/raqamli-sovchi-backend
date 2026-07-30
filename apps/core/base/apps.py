from django.apps import AppConfig
from django.apps import apps
from django.db.models.signals import class_prepared

def register_auditlog(sender, **kwargs):
    from auditlog.registry import auditlog
    from apps.core.base.models import BaseModel

    if issubclass(sender, BaseModel) and not sender._meta.abstract:
        try:
            auditlog.register(sender)
        except Exception:
            pass

class BaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core.base"
    verbose_name = "Baza"

    def ready(self):
        class_prepared.connect(register_auditlog)

        from auditlog.registry import auditlog
        from apps.core.base.models import BaseModel

        for model in apps.get_models():
            if issubclass(model, BaseModel) and not model._meta.abstract:
                try:
                    auditlog.register(model)
                except Exception:
                    pass
