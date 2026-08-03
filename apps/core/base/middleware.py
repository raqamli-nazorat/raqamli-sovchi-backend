from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication


class BlockedUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            try:
                auth_result = self.jwt_auth.authenticate(request)
                if auth_result:
                    user, _ = auth_result
                    request.user = user
            except Exception:
                pass

        if user and user.is_authenticated:
            if getattr(user, "is_blocked", False):
                return JsonResponse(
                    {
                        "detail": "Sizning hisobingiz bloklangan. Tizimdan foydalanish va so'rov yuborish huquqingiz cheklangan."
                    },
                    status=403,
                )

        return self.get_response(request)
