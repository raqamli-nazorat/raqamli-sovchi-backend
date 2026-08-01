import logging
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def get_bot_username():
    cache_key = "telegram_bot_username"
    cached_username = cache.get(cache_key)
    if cached_username:
        return cached_username

    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        return getattr(settings, "TELEGRAM_BOT_USERNAME", "RaqamliSovchiBot")

    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and "result" in data:
                username = data["result"].get("username")
                if username:
                    cache.set(cache_key, username, timeout=86400)
                    return username
    except Exception as e:
        logger.warning(f"Telegram getMe chaqirishda xatolik: {e}")

    return getattr(settings, "TELEGRAM_BOT_USERNAME", "RaqamliSovchiBot")
