import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.users.models import User, AuthProvider
from apps.accounts.telegram_bot.models import (
    TelegramAuthSession,
    SessionStatus,
)
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
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    session_id = command.args

    if session_id:
        session = await TelegramAuthSession.objects.filter(
            session_id=session_id, status=SessionStatus.PENDING
        ).afirst()

        if not session or timezone.now() >= session.expires_at:
            await message.answer(
                "⚠️ <b>Kirish sessiyasi topilmadi yoki muddati o'tgan.</b>\n\n"
                "<i>Iltimos, ilovadan qaytadan 'Telegram orqali kirish' tugmasini bosing.</i>"
            )
            return

        await state.update_data(session_id=str(session.session_id))
        await state.set_state(AuthStates.waiting_for_phone)
        await message.answer(
            "👋 <b>Raqamli Sovchi platformasiga xush kelibsiz!</b>\n\n"
            "<i>Tizimga kirish va shaxsingizni tasdiqlash uchun pastdagi tugma orqali telefon raqamingizni yuboring.</i>",
            reply_markup=phone_keyboard(),
        )
    else:
        await state.set_state(AuthStates.waiting_for_phone)
        await message.answer(
            "👋 <b>Raqamli Sovchi botiga xush kelibsiz!</b>\n\n"
            "<i>Tizimga kirish uchun telefon raqamingizni yuboring.</i>",
            reply_markup=phone_keyboard(),
        )


@router.message(AuthStates.waiting_for_phone, F.contact)
async def handle_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    data = await state.get_data()
    session_id = data.get("session_id")

    user, created = await User.objects.aget_or_create(
        phone_number=phone,
        defaults={"auth_provider": AuthProvider.TELEGRAM},
    )
    if not created and user.auth_provider != AuthProvider.TELEGRAM:
        user.auth_provider = AuthProvider.TELEGRAM
        await user.asave(update_fields=["auth_provider"])

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    if session_id:
        session = await TelegramAuthSession.objects.filter(
            session_id=session_id
        ).afirst()
        if session:
            session.status = SessionStatus.AUTHENTICATED
            session.user = user
            session.access_token = access_token
            session.refresh_token = refresh_token
            await session.asave(
                update_fields=["status", "user", "access_token", "refresh_token"]
            )

    await state.clear()
    await message.answer(
        "✅ <b>Tizimdan muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
        "<i>Veb/Mobile ilovaga qaytishingiz va foydalanishni davom ettirishingiz mumkin.</i>",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(AuthStates.waiting_for_phone)
async def handle_wrong_input(message: Message):
    await message.answer(
        "⚠️ <b>Telefon raqamni faqat tugma orqali yuboring.</b>\n\n"
        "<i>Quyidagi tugmani bosing.</i>",
        reply_markup=phone_keyboard(),
    )
