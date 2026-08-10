from rest_framework import permissions


class ProfileMePermission(permissions.BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_staff or request.user.is_superuser:
            return True

        if request.method == "DELETE":
            return request.user.has_perm("profiles.delete_me_profile")

        if request.method in ["PUT", "PATCH"]:
            return request.user.has_perm("profiles.change_me_profile")

        return True


class IsProfileOwnerOrStaff(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user.is_staff or request.user.is_superuser:
            return True

        return getattr(obj, "user_id", None) == request.user.id

