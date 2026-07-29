import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from apps.telegram_bot.bot.handlers import router


class Command(BaseCommand):
    help = "Telegram botni ishga tushiradi"

    def handle(self, *args, **kwargs):
        asyncio.run(self._run())

    async def _run(self):
        bot = Bot(
            token=settings.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)

        self.stdout.write(self.style.SUCCESS("Telegram bot ishga tushdi..."))
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
