from rest_framework import permissions


class IsStaffMember(permissions.BasePermission):
    """Faqat admin panelga kira oladigan xodimlar (is_staff yoki standart bo'lmagan rol)."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        return bool(user.is_staff or (user.role and not user.role.is_default))
