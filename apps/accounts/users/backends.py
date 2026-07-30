from django.contrib.auth.backends import ModelBackend


class RoleBackend(ModelBackend):
    def get_group_permissions(self, user_obj, obj=None):
        if (
            user_obj.is_anonymous
            or not getattr(user_obj, "role", None)
            or not user_obj.is_active
        ):
            return set()

        perms = user_obj.role.permissions.all()
        return {f"{p.content_type.app_label}.{p.codename}" for p in perms}
