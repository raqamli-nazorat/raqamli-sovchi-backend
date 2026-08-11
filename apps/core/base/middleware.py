from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication


class BlockedUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        user = getattr(request, "user", None)

        validated_token = None

        if not user or not user.is_authenticated:
            try:
                auth_result = self.jwt_auth.authenticate(request)
                if auth_result:
                    user, validated_token = auth_result
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

            device_id = request.headers.get("X-Device-Id") or request.META.get(
                "HTTP_X_DEVICE_ID"
            )

            if not device_id:
                if not validated_token:
                    try:
                        header = self.jwt_auth.get_header(request)
                        if header:
                            raw_token = self.jwt_auth.get_raw_token(header)
                            if raw_token:
                                validated_token = self.jwt_auth.get_validated_token(
                                    raw_token
                                )
                    except Exception:
                        pass

                if validated_token:
                    device_id = validated_token.get("device_id")

            if device_id:
                from apps.accounts.users.services import is_device_active_in_redis

                if not is_device_active_in_redis(user.id, device_id):
                    return JsonResponse(
                        {
                            "detail": "Ushbu qurilma seansi tugatilgan. Qaytadan tizimga kiring.",
                            "_error_code": "device_revoked",
                        },
                        status=401,
                    )

        return self.get_response(request)
