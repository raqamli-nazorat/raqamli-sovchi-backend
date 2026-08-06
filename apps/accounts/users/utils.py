from rest_framework_simplejwt.tokens import RefreshToken


def get_tokens_for_user(user, device_id=None):
    refresh = RefreshToken.for_user(user)
    if device_id:
        refresh["device_id"] = str(device_id)
        refresh.access_token["device_id"] = str(device_id)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
