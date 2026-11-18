import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.database import async_session_maker
from app.models.models import User
from app.services.auth_service import register_telegram_user
from bot.keyboards import (
    BTN_CANCEL,
    cancel_keyboard,
    consent_keyboard,
    contact_keyboard,
    main_menu_keyboard,
    survey_age_keyboard,
    survey_interest_keyboard,
    survey_level_keyboard,
    survey_region_keyboard,
    survey_source_keyboard,
)
from bot.states import RegistrationState
from bot.texts import (
    INTEREST_OPTIONS,
    REGION_OPTIONS,
    SOURCE_OPTIONS,
    STATUS_LABELS,
    escape_html,
    get_rules_text,
    send_long_message,
)
from bot.utils import normalize_uz_phone, send_otp_message

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("cancel"))
@router.message(F.text == BTN_CANCEL)
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session_maker() as db:
        res = await db.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one_or_none()
    if user:
        await message.answer("Amal bekor qilindi.", reply_markup=main_menu_keyboard())
    else:
        await message.answer(
            "Ro'yxatdan o'tish bekor qilindi. Qaytadan boshlash uchun /start bosing.",
            reply_markup=ReplyKeyboardRemove(),
        )


@router.callback_query(F.data == "survey_cancel")
async def cb_survey_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Ro'yxatdan o'tish bekor qilindi. Qaytadan boshlash uchun /start bosing.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await callback.answer()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg_id = message.from_user.id

    async with async_session_maker() as db:
        res = await db.execute(select(User).where(User.telegram_id == tg_id))
        existing_user = res.scalar_one_or_none()

    if existing_user:
        status_label = STATUS_LABELS.get(existing_user.status, existing_user.status)
        await message.answer(
            f"👋 Xush kelibsiz, <b>{escape_html(existing_user.full_name or existing_user.username)}</b>!\n"
            f"Loginingiz: <code>{escape_html(existing_user.login)}</code>\n"
            f"Holatingiz: <b>{escape_html(status_label)}</b>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
        return

    if settings.today_local() > settings.registration_close:
        await message.answer(
            "⛔ Ro'yxatdan o'tish yopilgan.\n"
            f"Ro'yxatdan o'tish muddati: {settings.REGISTRATION_CLOSE_DATE} gacha edi.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await message.answer(
        "🐍 <b>PyChallenge</b> — 30 kunlik Python musobaqasiga xush kelibsiz!\n\n"
        "Ro'yxatdan o'tishdan oldin quyidagi qoidalar bilan tanishib chiqing:",
        parse_mode="HTML",
    )
    await send_long_message(
        message,
        get_rules_text(),
        parse_mode="HTML",
        reply_markup=consent_keyboard(),
    )
    await state.set_state(RegistrationState.waiting_consent)


@router.callback_query(RegistrationState.waiting_consent, F.data == "consent:decline")
async def cb_consent_decline(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Qoidalarga rozilik bermaganingiz sababli ro'yxatdan o'tish bekor qilindi.\n"
        "Fikringiz o'zgarsa /start buyrug'ini yuboring."
    )
    await callback.answer()


@router.callback_query(RegistrationState.waiting_consent, F.data == "consent:agree")
async def cb_consent_agree(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(
        consent_version=settings.RULES_VERSION,
        consent_at=datetime.now(timezone.utc).isoformat(),
    )
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "✅ Qoidalarga rozilik qabul qilindi.\n\n"
        "Endi telefon raqamingizni ulashing (faqat +998 bilan boshlanuvchi o'z raqamingiz):",
        reply_markup=contact_keyboard(),
    )
    await state.set_state(RegistrationState.waiting_phone)
    await callback.answer()


@router.message(RegistrationState.waiting_phone, F.contact)
async def handle_phone_contact(message: Message, state: FSMContext) -> None:
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer(
            "❌ Boshqa odamning kontaktini yuborish mumkin emas. "
            "Pastdagi «📱 Raqamni ulashish» tugmasi orqali o'z raqamingizni yuboring.",
            reply_markup=contact_keyboard(),
        )
        return

    phone = normalize_uz_phone(contact.phone_number)
    if not phone:
        await message.answer(
            "❌ Faqat O'zbekiston raqamlari (+998XXXXXXXXX) qabul qilinadi. "
            "Iltimos, +998 bilan boshlanuvchi raqamingizni ulashing.",
            reply_markup=contact_keyboard(),
        )
        return

    async with async_session_maker() as db:
        tg_res = await db.execute(select(User).where(User.telegram_id == message.from_user.id))
        if tg_res.scalar_one_or_none():
            await state.clear()
            await message.answer(
                "Siz allaqachon ro'yxatdan o'tgansiz.",
                reply_markup=main_menu_keyboard(),
            )
            return

        phone_res = await db.execute(select(User).where(User.phone == phone))
        if phone_res.scalar_one_or_none():
            await message.answer(
                "❌ Bu raqam bilan allaqachon ro'yxatdan o'tilgan. Muammo bo'lsa adminga yozing.",
                reply_markup=contact_keyboard(),
            )
            return

    await state.update_data(phone=phone)
    await message.answer(
        "👤 To'liq ism-familiyangizni kiriting (2-100 belgi):\n\n"
        "⚠️ <i>Eslatma: Mukofot karta egasining ismi shu ism bilan mos bo'lishi shart.</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(RegistrationState.waiting_full_name)


@router.message(RegistrationState.waiting_phone)
async def handle_phone_invalid(message: Message) -> None:
    await message.answer(
        "Iltimos, telefon raqamini matn ko'rinishida yozmang — pastdagi «📱 Raqamni ulashish» tugmasini bosing.",
        reply_markup=contact_keyboard(),
    )


@router.message(RegistrationState.waiting_full_name, F.text)
async def handle_full_name(message: Message, state: FSMContext) -> None:
    full_name = message.text.strip()
    if len(full_name) < 2 or len(full_name) > 100:
        await message.answer("❌ Ism-familiya 2 dan 100 belgigacha bo'lishi kerak. Qaytadan kiriting:")
        return

    await state.update_data(full_name=full_name)
    await message.answer(
        "📊 Qisqa so'rovnoma (1/5):\n\n<b>Python bo'yicha hozirgi darajangiz qanday?</b>",
        parse_mode="HTML",
        reply_markup=survey_level_keyboard(),
    )
    await state.set_state(RegistrationState.waiting_level)


@router.callback_query(RegistrationState.waiting_level, F.data.startswith("survey_level:"))
async def cb_survey_level(callback: CallbackQuery, state: FSMContext) -> None:
    level = callback.data.split(":", 1)[1]
    await state.update_data(self_level=level)
    await callback.message.edit_text(
        "📊 Qisqa so'rovnoma (2/5):\n\n<b>Yosh guruhingizni tanlang:</b>",
        parse_mode="HTML",
        reply_markup=survey_age_keyboard(),
    )
    await state.set_state(RegistrationState.waiting_age)
    await callback.answer()


@router.callback_query(RegistrationState.waiting_age, F.data.startswith("survey_age:"))
async def cb_survey_age(callback: CallbackQuery, state: FSMContext) -> None:
    age_group = callback.data.split(":", 1)[1]
    await state.update_data(age_group=age_group)
    await callback.message.edit_text(
        "📊 Qisqa so'rovnoma (3/5):\n\n<b>Qaysi hududdansiz?</b>",
        parse_mode="HTML",
        reply_markup=survey_region_keyboard(),
    )
    await state.set_state(RegistrationState.waiting_region)
    await callback.answer()


@router.callback_query(RegistrationState.waiting_region, F.data.startswith("survey_region:"))
async def cb_survey_region(callback: CallbackQuery, state: FSMContext) -> None:
    idx = int(callback.data.split(":", 1)[1])
    region = REGION_OPTIONS[idx]
    await state.update_data(region=region)
    await callback.message.edit_text(
        "📊 Qisqa so'rovnoma (4/5):\n\n<b>Bizni qayerdan topdingiz?</b>",
        parse_mode="HTML",
        reply_markup=survey_source_keyboard(),
    )
    await state.set_state(RegistrationState.waiting_source)
    await callback.answer()


@router.callback_query(RegistrationState.waiting_source, F.data.startswith("survey_source:"))
async def cb_survey_source(callback: CallbackQuery, state: FSMContext) -> None:
    idx = int(callback.data.split(":", 1)[1])
    source = SOURCE_OPTIONS[idx]
    await state.update_data(source=source)
    await callback.message.edit_text(
        "📊 Qisqa so'rovnoma (5/5):\n\n<b>Qaysi yo'nalish sizga ko'proq qiziq? (keyingi mavsumlar uchun)</b>",
        parse_mode="HTML",
        reply_markup=survey_interest_keyboard(),
    )
    await state.set_state(RegistrationState.waiting_interest)
    await callback.answer()


@router.callback_query(RegistrationState.waiting_interest, F.data.startswith("survey_interest:"))
async def cb_survey_interest(callback: CallbackQuery, state: FSMContext) -> None:
    idx = int(callback.data.split(":", 1)[1])
    interest = INTEREST_OPTIONS[idx]
    data = await state.get_data()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)

    tg_id = callback.from_user.id
    tg_username = callback.from_user.username
    consent_at = datetime.fromisoformat(data["consent_at"])

    try:
        async with async_session_maker() as db:
            async with db.begin():
                # Double-check inside transaction
                existing_tg = await db.execute(select(User).where(User.telegram_id == tg_id))
                if existing_tg.scalar_one_or_none():
                    await callback.message.answer(
                        "Siz allaqachon ro'yxatdan o'tgansiz.",
                        reply_markup=main_menu_keyboard(),
                    )
                    await callback.answer()
                    return

                existing_phone = await db.execute(select(User).where(User.phone == data["phone"]))
                if existing_phone.scalar_one_or_none():
                    await callback.message.answer(
                        "❌ Bu raqam bilan allaqachon ro'yxatdan o'tilgan. Muammo bo'lsa adminga yozing.",
                        reply_markup=ReplyKeyboardRemove(),
                    )
                    await callback.answer()
                    return

                user, otp_plain, waitlist_pos = await register_telegram_user(
                    db,
                    telegram_id=tg_id,
                    phone=data["phone"],
                    full_name=data["full_name"],
                    username=tg_username,
                    self_level=data["self_level"],
                    age_group=data["age_group"],
                    region=data["region"],
                    source=data["source"],
                    interest=interest,
                    consent_version=data["consent_version"],
                    consent_at=consent_at,
                )
    except IntegrityError:
        logger.warning("Ro'yxatdan o'tishda takroriy ma'lumot (tg_id=%s)", tg_id)
        await callback.message.answer(
            "❌ Bu Telegram akkaunt yoki telefon raqami bilan allaqachon ro'yxatdan o'tilgan.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await callback.answer()
        return

    if otp_plain is not None:
        await callback.message.answer(
            "🎉 <b>Tabriklaymiz! Ro'yxatdan o'tish muvaffaqiyatli yakunlandi.</b>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
        await send_otp_message(callback.bot, tg_id, user.login, otp_plain)
    else:
        await callback.message.answer(
            f"⏳ <b>Joylar hozircha to'lgan ({settings.MAX_PARTICIPANTS}/{settings.MAX_PARTICIPANTS}).</b>\n\n"
            f"Siz kutish ro'yxatidasiz (<b>{waitlist_pos}-o'rin</b>).\n"
            "Joy bo'shasa sizga darhol xabar beramiz!",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )

    await callback.answer()
