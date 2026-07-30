from django.contrib.auth.models import (
    Permission,
    _user_get_permissions,
    _user_has_module_perms,
    _user_has_perm,
)
from django.db import models


class RolePermissionsMixin(models.Model):
    is_superuser = models.BooleanField(default=False)
    role = models.ForeignKey(
        "users.Role",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Rol",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name="Maxsus huquqlar",
        blank=True,
    )

    class Meta:
        abstract = True

    def get_user_permissions(self, obj=None):
        return _user_get_permissions(self, obj, "user")

    def get_group_permissions(self, obj=None):
        return _user_get_permissions(self, obj, "group")

    def get_all_permissions(self, obj=None):
        return _user_get_permissions(self, obj, "all")

    def has_perm(self, perm, obj=None):
        if getattr(self, "is_active", True) and self.is_superuser:
            return True
        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list, obj=None):
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        if getattr(self, "is_active", True) and self.is_superuser:
            return True
        return _user_has_module_perms(self, app_label)
