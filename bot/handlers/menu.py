import logging
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select, update

from app.core.config import settings
from app.db.database import async_session_maker
from app.models.models import ExamSession, Submission, SupportMessage, User, ViolationLog
from app.services.auth_service import (
    OtpRateLimitError,
    confirm_participation,
    create_otp_for_user,
    get_waitlist_position,
)
from bot.keyboards import (
    BTN_CONTACT_ADMIN,
    BTN_MY_RESULTS,
    BTN_MY_STATUS,
    BTN_RESET_PASSWORD,
    BTN_RULES,
    cancel_keyboard,
    contact_admin_inline_keyboard,
    main_menu_keyboard,
)
from bot.states import SupportState
from bot.texts import STATUS_LABELS, escape_html, get_rules_text, send_long_message
from bot.utils import send_otp_message

logger = logging.getLogger(__name__)
router = Router()

_SUPPORT_ID_RE = re.compile(r"\((\d+)\):")


async def _get_user_by_tg(tg_id: int) -> User | None:
    async with async_session_maker() as db:
        res = await db.execute(select(User).where(User.telegram_id == tg_id))
        return res.scalar_one_or_none()


@router.message(F.text == BTN_RESET_PASSWORD)
async def handle_reset_password(message: Message) -> None:
    tg_id = message.from_user.id
    async with async_session_maker() as db:
        async with db.begin():
            res = await db.execute(select(User).where(User.telegram_id == tg_id))
            user = res.scalar_one_or_none()
            if not user:
                await message.answer("Avval /start orqali ro'yxatdan o'ting.")
                return

            if user.status == "waitlist":
                await message.answer(
                    "⏳ Siz hozircha kutish ro'yxatidasiz. Joy bo'shaganda sizga parol yuboriladi."
                )
                return
            if user.status == "expired":
                await message.answer(
                    "⌛ Tasdiqlash muddati tugaganligi sababli parol berilmaydi."
                )
                return
            if user.status == "disqualified":
                reason = user.disqualified_reason or "Qoidabuzarlik"
                await message.answer(
                    f"⛔ Siz diskvalifikatsiya qilingansiz.\nSabab: {escape_html(reason)}",
                    parse_mode="HTML",
                    reply_markup=contact_admin_inline_keyboard(),
                )
                return
            if user.status == "banned":
                await message.answer("🚫 Akkauntingiz bloklangan.")
                return
            if user.status not in ("registered", "confirmed"):
                await message.answer("❌ Hozirgi holatingizda parol tiklash mumkin emas.")
                return

            try:
                otp_plain = await create_otp_for_user(
                    db, user, invalidate_permanent_password=True
                )
            except OtpRateLimitError as err:
                await message.answer(f"⏳ {err}")
                return

    await send_otp_message(
        message.bot,
        tg_id,
        user.login,
        otp_plain,
        prefix="🔑 <b>Parol tiklandi!</b> Eski doimiy parolingiz bekor qilindi.\n\n",
    )


@router.message(F.text == BTN_MY_RESULTS)
async def handle_my_results(message: Message) -> None:
    tg_id = message.from_user.id
    async with async_session_maker() as db:
        res = await db.execute(select(User).where(User.telegram_id == tg_id))
        user = res.scalar_one_or_none()
        if not user:
            await message.answer("Avval /start orqali ro'yxatdan o'ting.")
            return

        if settings.today_local() < settings.challenge_start:
            await message.answer(
                f"📅 Challenge hali boshlanmagan.\n"
                f"Boshlanish sanasi: <b>{settings.CHALLENGE_START_DATE}</b>",
                parse_mode="HTML",
            )
            return

        days_res = await db.execute(
            select(func.count(func.distinct(Submission.challenge_day_id))).where(
                Submission.user_id == user.id
            )
        )
        days_submitted = int(days_res.scalar() or 0)

        rank_res = await db.execute(
            select(func.count(User.id)).where(
                User.status == "confirmed",
                User.total_score > (user.total_score or 0),
            )
        )
        rank = int(rank_res.scalar() or 0) + 1

        viol_res = await db.execute(
            select(func.count(ViolationLog.id))
            .join(ExamSession, ViolationLog.session_id == ExamSession.id)
            .where(ExamSession.user_id == user.id)
        )
        violations_count = int(viol_res.scalar() or 0)

    await message.answer(
        f"📊 <b>Mening natijam</b>\n\n"
        f"👤 Ism: {escape_html(user.full_name or user.username)}\n"
        f"🏆 Umumiy ball: <b>{user.total_score or 0}</b>\n"
        f"📅 Topshirilgan kunlar: <b>{days_submitted}</b>\n"
        f"🥇 Joriy o'rin: <b>#{rank}</b>\n"
        f"⚠️ Qoidabuzarliklar: <b>{violations_count}</b>",
        parse_mode="HTML",
    )


@router.message(F.text == BTN_RULES)
async def handle_rules(message: Message) -> None:
    await send_long_message(message, get_rules_text(), parse_mode="HTML")


@router.message(F.text == BTN_MY_STATUS)
async def handle_my_status(message: Message) -> None:
    tg_id = message.from_user.id
    async with async_session_maker() as db:
        res = await db.execute(select(User).where(User.telegram_id == tg_id))
        user = res.scalar_one_or_none()
        if not user:
            await message.answer("Avval /start orqali ro'yxatdan o'ting.")
            return

        waitlist_pos = await get_waitlist_position(db, user) if user.status == "waitlist" else None

    status_label = STATUS_LABELS.get(user.status, user.status)
    lines = [
        "ℹ️ <b>Mening holatim</b>\n",
        f"👤 Ism: {escape_html(user.full_name or user.username)}",
        f"🆔 Login: <code>{escape_html(user.login)}</code>",
        f"📌 Holat: <b>{escape_html(status_label)}</b>",
    ]
    if waitlist_pos is not None:
        lines.append(f"⏳ Kutish o'rni: <b>{waitlist_pos}-o'rin</b>")
    if user.status == "disqualified" and user.disqualified_reason:
        lines.append(f"❗ Sabab: {escape_html(user.disqualified_reason)}")

    lines.extend(
        [
            "",
            f"📅 Tasdiqlash oynasi: {settings.CONFIRM_WINDOW_START} — {settings.CONFIRM_WINDOW_END}",
            f"🚀 Challenge boshlanishi: {settings.CHALLENGE_START_DATE}",
            f"🏁 Yakuniy sana: {settings.FINAL_DATE}",
            f"🔔 Kunlik eslatmalar: {'O‘chirilgan (/mute)' if user.notifications_muted else 'Yoqilgan'}",
        ]
    )

    markup = contact_admin_inline_keyboard() if user.status == "disqualified" else None
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=markup)


@router.message(Command("mute"))
async def cmd_mute(message: Message) -> None:
    tg_id = message.from_user.id
    async with async_session_maker() as db:
        async with db.begin():
            res = await db.execute(select(User).where(User.telegram_id == tg_id))
            user = res.scalar_one_or_none()
            if not user:
                await message.answer("Avval /start orqali ro'yxatdan o'ting.")
                return
            user.notifications_muted = not bool(user.notifications_muted)
            muted = user.notifications_muted

    if muted:
        await message.answer("🔕 Kunlik eslatmalar o'chirildi. Qayta yoqish uchun /mute yuboring.")
    else:
        await message.answer("🔔 Kunlik eslatmalar qayta yoqildi.")


@router.callback_query(F.data == "confirm_participation")
async def cb_confirm_participation(callback: CallbackQuery) -> None:
    tg_id = callback.from_user.id
    async with async_session_maker() as db:
        async with db.begin():
            res = await db.execute(select(User).where(User.telegram_id == tg_id))
            user = res.scalar_one_or_none()
            if not user:
                await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
                return

            if user.status == "confirmed":
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.answer("Siz allaqachon tasdiqlagansiz ✅", show_alert=True)
                return

            if user.status != "registered":
                await callback.answer(
                    f"Hozirgi holatingizda tasdiqlash mumkin emas ({user.status}).",
                    show_alert=True,
                )
                return

            await confirm_participation(db, user)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✅ <b>Qatnashishingiz tasdiqlandi!</b>\n"
        f"Challenge <b>{settings.CHALLENGE_START_DATE}</b> kuni Toshkent vaqti bilan 00:00 da boshlanadi.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer("Tasdiqlandi!")


@router.message(F.text == BTN_CONTACT_ADMIN)
async def handle_contact_admin(message: Message, state: FSMContext) -> None:
    user = await _get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali ro'yxatdan o'ting.")
        return

    await state.set_state(SupportState.waiting_message)
    await message.answer(
        "📩 Adminga yubormoqchi bo'lgan xabaringizni yozing:",
        reply_markup=cancel_keyboard(),
    )


@router.callback_query(F.data == "open_support")
async def cb_open_support(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SupportState.waiting_message)
    await callback.message.answer(
        "📩 Adminga yubormoqchi bo'lgan xabaringizni yozing:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(SupportState.waiting_message, F.text)
async def handle_support_text(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if not text:
        await message.answer("Bo'sh xabar yuborib bo'lmaydi. Qaytadan yozing:")
        return

    await state.clear()
    tg_id = message.from_user.id

    async with async_session_maker() as db:
        async with db.begin():
            res = await db.execute(select(User).where(User.telegram_id == tg_id))
            user = res.scalar_one_or_none()
            if not user:
                await message.answer("Foydalanuvchi topilmadi.")
                return
            db.add(SupportMessage(user_id=user.id, text=text))

    display_name = escape_html(user.full_name or user.username)
    escaped_text = escape_html(text)
    admin_msg = f"👤 <b>{display_name}</b> ({tg_id}):\n{escaped_text}"

    for admin_id in settings.admin_telegram_id_set:
        try:
            await message.bot.send_message(chat_id=admin_id, text=admin_msg, parse_mode="HTML")
        except Exception:
            logger.warning("Adminga support xabari yuborilmadi (admin_id=%s)", admin_id)

    await message.answer(
        "✅ Xabaringiz adminga yuborildi. Tez orada javob beramiz.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.reply_to_message, F.text, F.from_user.id.in_(settings.admin_telegram_id_set))
async def handle_admin_reply_to_support(message: Message) -> None:
    replied_text = message.reply_to_message.text or message.reply_to_message.caption or ""
    match = _SUPPORT_ID_RE.search(replied_text)
    if not match:
        return

    target_tg_id = int(match.group(1))
    reply_text = message.text.strip()
    if not reply_text:
        return

    try:
        await message.bot.send_message(
            chat_id=target_tg_id,
            text=f"📩 <b>Admin javobi:</b>\n\n{escape_html(reply_text)}",
            parse_mode="HTML",
        )
    except Exception:
        await message.answer("❌ Foydalanuvchiga xabar yuborib bo'lmadi.")
        return

    async with async_session_maker() as db:
        async with db.begin():
            res = await db.execute(select(User).where(User.telegram_id == target_tg_id))
            user = res.scalar_one_or_none()
            if user:
                await db.execute(
                    update(SupportMessage)
                    .where(SupportMessage.user_id == user.id, SupportMessage.answered.is_(False))
                    .values(answered=True)
                )

    await message.answer("✅ Javob foydalanuvchiga yuborildi.")
