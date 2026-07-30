import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from apps.accounts.telegram_bot.models import LoginCode
from .states import AuthStates

router = Router()

def phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Telefon raqamni ulashish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(AuthStates.waiting_for_phone)
    await message.answer(
        "👋 <b>Raqamli Sovchi ga xush kelibsiz!</b>\n\n"
        "<i>Tizimga kirish uchun telefon raqamingizni yuboring.</i>",
        reply_markup=phone_keyboard(),
    )

@router.message(AuthStates.waiting_for_phone, F.contact)
async def handle_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    login_code = await LoginCode.objects.acreate(phone_number=phone)

    await state.clear()
    await message.answer(
        f"🔐 <b>Tasdiqlash kodingiz:</b> <code>{login_code.code}</code>\n\n"
        f"<i>Kod 5 daqiqa davomida amal qiladi.</i>",
        reply_markup=ReplyKeyboardRemove(),
    )

@router.message(AuthStates.waiting_for_phone)
async def handle_wrong_input(message: Message):
    await message.answer(
        "⚠️ <b>Telefon raqamni faqat tugma orqali yuboring.</b>\n\n"
        "<i>Quyidagi tugmani bosing.</i>",
        reply_markup=phone_keyboard(),
    )
