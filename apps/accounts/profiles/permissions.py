from rest_framework import permissions


class ProfileMePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsProfileOwnerOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user.is_superuser:
            return True

        if request.user.is_staff or bool(request.user.role and not request.user.role.is_default):
            if request.method == "POST":
                return request.user.has_perm("profiles.add_profile")
            if request.method in ["PUT", "PATCH"]:
                return request.user.has_perm("profiles.change_profile")
            if request.method == "DELETE":
                return request.user.has_perm("profiles.delete_profile")

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method in ["PUT", "PATCH", "DELETE", "POST"]:
            return True

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if user.is_superuser:
            return True

        if user.is_staff or bool(user.role and not user.role.is_default):
            if request.method in ["PUT", "PATCH"]:
                return user.has_perm("profiles.change_profile")
            if request.method == "DELETE":
                return user.has_perm("profiles.delete_profile")

        if getattr(obj, "user_id", None) == user.id:
            return True

        if hasattr(obj, "representative_info") and obj.representative_info:
            rep_profile = getattr(user, "profile", None)
            if rep_profile and obj.representative_info.profile_id == rep_profile.id:
                return True

        return False
