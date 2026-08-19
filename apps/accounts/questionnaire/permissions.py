from rest_framework import permissions


class IsUserAnswerOwnerOrStaff(permissions.BasePermission):
    """
    UserAnswer obyekti uchun permission classi.
    - Avtorizatsiyadan o'tgan foydalanuvchilar o'z profillarining javoblarini ko'rishi va boshqarishi mumkin.
    - Staff/Admin foydalanuvchilar tegishli Django modellari huquqiga ko'ra ruxsat oladi.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        if request.user.is_staff or bool(
            request.user.role and not request.user.role.is_default
        ):
            if request.method == "POST":
                return request.user.has_perm("questionnaire.add_useranswer")
            if request.method in ["PUT", "PATCH"]:
                return request.user.has_perm("questionnaire.change_useranswer")
            if request.method == "DELETE":
                return request.user.has_perm("questionnaire.delete_useranswer")

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if user.is_staff or bool(user.role and not user.role.is_default):
            if request.method in ["PUT", "PATCH"]:
                return user.has_perm("questionnaire.change_useranswer")
            if request.method == "DELETE":
                return user.has_perm("questionnaire.delete_useranswer")
            if request.method in permissions.SAFE_METHODS:
                return user.has_perm("questionnaire.view_useranswer")

        user_profile = getattr(user, "profile", None)
        if user_profile and getattr(obj, "profile_id", None) == user_profile.id:
            return True

        return False
