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


HasChangeMeProfilePermission = ProfileMePermission
