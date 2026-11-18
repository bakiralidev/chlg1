import asyncio
import io
import logging

import openpyxl
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from sqlalchemy import func, select, update

from app.core.config import settings
from app.db.database import async_session_maker
from app.models.models import BroadcastLog, SupportMessage, User
from bot.keyboards import contact_admin_inline_keyboard
from bot.texts import STATUS_LABELS, escape_html

logger = logging.getLogger(__name__)
router = Router()

# All handlers in this router require ADMIN_TELEGRAM_IDS membership
router.message.filter(F.from_user.id.in_(settings.admin_telegram_id_set))

_VALID_STATUSES = {"registered", "waitlist", "confirmed", "expired", "disqualified", "banned"}


async def _find_user_by_identifier(db, identifier: str) -> User | None:
    ident = identifier.strip()
    if ident.lstrip("-").isdigit():
        res = await db.execute(select(User).where(User.telegram_id == int(ident)))
        user = res.scalar_one_or_none()
        if user:
            return user
    res = await db.execute(select(User).where(User.login == ident))
    return res.scalar_one_or_none()


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    async with async_session_maker() as db:
        res = await db.execute(select(User.status, func.count(User.id)).group_by(User.status))
        counts = dict(res.all())
        total_res = await db.execute(select(func.count(User.id)))
        total = int(total_res.scalar() or 0)

    lines = [
        "📊 <b>Platforma statistikasi</b>\n",
        f"👥 Jami foydalanuvchilar: <b>{total}</b>",
        f"📝 Ro'yxatdan o'tgan (registered): <b>{counts.get('registered', 0)}</b>",
        f"✅ Tasdiqlagan (confirmed): <b>{counts.get('confirmed', 0)}</b>",
        f"⏳ Kutish ro'yxati (waitlist): <b>{counts.get('waitlist', 0)}</b>",
        f"⌛ Muddati o'tgan (expired): <b>{counts.get('expired', 0)}</b>",
        f"⛔ Diskvalifikatsiya (disqualified): <b>{counts.get('disqualified', 0)}</b>",
        f"🚫 Bloklangan (banned): <b>{counts.get('banned', 0)}</b>",
    ]
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 2:
        await message.answer(
            "Foydalanish:\n"
            "<code>/broadcast Xabar matni</code>\n"
            "<code>/broadcast confirmed Xabar matni</code>",
            parse_mode="HTML",
        )
        return

    target_status = None
    if len(parts) >= 3 and parts[1].lower() in _VALID_STATUSES:
        target_status = parts[1].lower()
        text_to_send = parts[2]
    else:
        text_to_send = (message.text or "").split(maxsplit=1)[1]

    async with async_session_maker() as db:
        query = select(User.telegram_id).where(User.telegram_id.is_not(None))
        if target_status:
            query = query.where(User.status == target_status)
        res = await db.execute(query)
        recipient_ids = [row[0] for row in res.all()]

    if not recipient_ids:
        await message.answer("Yuborish uchun foydalanuvchilar topilmadi.")
        return

    await message.answer(f"📤 Xabar {len(recipient_ids)} ta foydalanuvchiga yuborilmoqda...")

    sent_count = 0
    failed_count = 0
    safe_text = escape_html(text_to_send)

    for tg_id in recipient_ids:
        try:
            await message.bot.send_message(chat_id=tg_id, text=safe_text, parse_mode="HTML")
            sent_count += 1
        except Exception:
            failed_count += 1
        # Telegram rate limit (~25 msg/sec)
        await asyncio.sleep(0.04)

    async with async_session_maker() as db:
        async with db.begin():
            db.add(
                BroadcastLog(
                    admin_telegram_id=message.from_user.id,
                    text=text_to_send,
                    sent_count=sent_count,
                    failed_count=failed_count,
                )
            )

    await message.answer(
        f"✅ Broadcast yakunlandi.\nYuborildi: <b>{sent_count}</b>\nXato: <b>{failed_count}</b>",
        parse_mode="HTML",
    )


@router.message(Command("ban"))
async def cmd_ban(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Foydalanish: <code>/ban &lt;telegram_id yoki login&gt; &lt;sabab&gt;</code>", parse_mode="HTML")
        return

    ident, reason = parts[1], parts[2].strip()
    async with async_session_maker() as db:
        async with db.begin():
            user = await _find_user_by_identifier(db, ident)
            if not user:
                await message.answer("Foydalanuvchi topilmadi.")
                return
            user.status = "banned"
            user.disqualified_reason = reason
            tg_id = user.telegram_id
            login = user.login

    if tg_id:
        try:
            await message.bot.send_message(
                chat_id=tg_id,
                text=f"🚫 Akkauntingiz bloklandi.\nSabab: {escape_html(reason)}",
                parse_mode="HTML",
            )
        except Exception:
            pass

    await message.answer(f"🚫 Foydalanuvchi <code>{escape_html(login)}</code> bloklandi.", parse_mode="HTML")


@router.message(Command("unban"))
async def cmd_unban(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Foydalanish: <code>/unban &lt;telegram_id yoki login&gt;</code>", parse_mode="HTML")
        return

    ident = parts[1].strip()
    async with async_session_maker() as db:
        async with db.begin():
            user = await _find_user_by_identifier(db, ident)
            if not user:
                await message.answer("Foydalanuvchi topilmadi.")
                return
            user.status = "confirmed" if user.confirmed_at else "registered"
            user.disqualified_reason = None
            tg_id = user.telegram_id
            login = user.login
            new_status = user.status

    if tg_id:
        try:
            await message.bot.send_message(
                chat_id=tg_id,
                text=f"✅ Akkauntingiz blokdan chiqarildi. Joriy holat: {escape_html(new_status)}",
                parse_mode="HTML",
            )
        except Exception:
            pass

    await message.answer(f"✅ Foydalanuvchi <code>{escape_html(login)}</code> blokdan chiqarildi ({new_status}).", parse_mode="HTML")


@router.message(Command("disqualify"))
async def cmd_disqualify(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Foydalanish: <code>/disqualify &lt;login&gt; &lt;sabab&gt;</code>", parse_mode="HTML")
        return

    login_arg, reason = parts[1].strip(), parts[2].strip()
    async with async_session_maker() as db:
        async with db.begin():
            res = await db.execute(select(User).where(User.login == login_arg))
            user = res.scalar_one_or_none()
            if not user:
                await message.answer("Foydalanuvchi topilmadi.")
                return
            user.status = "disqualified"
            user.disqualified_reason = reason
            tg_id = user.telegram_id

    if tg_id:
        try:
            await message.bot.send_message(
                chat_id=tg_id,
                text=f"⛔ <b>Siz musobaqadan diskvalifikatsiya qilindingiz.</b>\nSabab: {escape_html(reason)}",
                parse_mode="HTML",
                reply_markup=contact_admin_inline_keyboard(),
            )
        except Exception:
            pass

    await message.answer(f"⛔ <code>{escape_html(login_arg)}</code> diskvalifikatsiya qilindi.", parse_mode="HTML")


@router.message(Command("user"))
async def cmd_user(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Foydalanish: <code>/user &lt;login yoki telegram_id&gt;</code>", parse_mode="HTML")
        return

    async with async_session_maker() as db:
        user = await _find_user_by_identifier(db, parts[1])
        if not user:
            await message.answer("Foydalanuvchi topilmadi.")
            return

    status_label = STATUS_LABELS.get(user.status, user.status)
    info = (
        f"👤 <b>Foydalanuvchi ma'lumotlari</b>\n\n"
        f"🆔 Login: <code>{escape_html(user.login)}</code>\n"
        f"📱 Telegram ID: <code>{user.telegram_id or '-'}</code>\n"
        f"📞 Telefon: {escape_html(user.phone or '-')}\n"
        f"📛 Ism-familiya: {escape_html(user.full_name or user.username)}\n"
        f"📌 Holat: <b>{escape_html(status_label)}</b>\n"
        f"💻 Daraja: {escape_html(user.self_level or '-')}\n"
        f"🎂 Yosh guruhi: {escape_html(user.age_group or '-')}\n"
        f"📍 Hudud: {escape_html(user.region or '-')}\n"
        f"📣 Manba: {escape_html(user.source or '-')}\n"
        f"🎯 Yo'nalish: {escape_html(user.interest or '-')}\n"
        f"🏆 Ball: <b>{user.total_score or 0}</b>\n"
        f"👑 Admin: {'Ha' if user.is_admin else 'Yo‘q'}"
    )
    await message.answer(info, parse_mode="HTML")


@router.message(Command("export"))
async def cmd_export(message: Message) -> None:
    async with async_session_maker() as db:
        res = await db.execute(select(User).order_by(User.created_at.asc()))
        users = res.scalars().all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ishtirokchilar"
    ws.append([
        "Login", "Ism-familiya", "Username", "Telefon", "Telegram ID",
        "Holat", "Daraja", "Yosh guruhi", "Hudud", "Manba", "Yo'nalish",
        "Ball", "Tasdiqlangan vaqt", "Ro'yxatdan o'tgan vaqt"
    ])

    for u in users:
        ws.append([
            u.login,
            u.full_name or "",
            u.username,
            u.phone or "",
            u.telegram_id or "",
            u.status,
            u.self_level or "",
            u.age_group or "",
            u.region or "",
            u.source or "",
            u.interest or "",
            u.total_score or 0,
            u.confirmed_at.isoformat() if u.confirmed_at else "",
            u.created_at.isoformat() if u.created_at else "",
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"pychallenge_users_{settings.today_local().isoformat()}.xlsx"
    doc = BufferedInputFile(buf.read(), filename=filename)
    await message.answer_document(doc, caption=f"📊 Jami {len(users)} ta foydalanuvchi")


@router.message(Command("reply"))
async def cmd_reply(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3 or not parts[1].lstrip("-").isdigit():
        await message.answer("Foydalanish: <code>/reply &lt;telegram_id&gt; &lt;matn&gt;</code>", parse_mode="HTML")
        return

    target_tg_id = int(parts[1])
    reply_text = parts[2].strip()

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

    await message.answer("✅ Javob yuborildi.")
