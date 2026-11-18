import asyncio
import logging
from datetime import datetime, time, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.config import settings
from app.db.database import async_session_maker
from app.models.models import Submission, User
from app.services.auth_service import expire_and_promote_waitlist
from bot.keyboards import confirm_participation_keyboard
from bot.utils import send_otp_message

logger = logging.getLogger(__name__)


async def send_confirmation_reminders(bot: Bot) -> None:
    today = settings.today_local()
    if not (settings.confirm_window_start_date <= today <= settings.confirm_window_end_date):
        return

    async with async_session_maker() as db:
        res = await db.execute(
            select(User).where(
                User.status == "registered",
                User.promoted_at.is_(None),
                User.telegram_id.is_not(None),
            )
        )
        users = res.scalars().all()

    is_first_day = today == settings.confirm_window_start_date
    text = (
        f"🚀 Challenge <b>{settings.CHALLENGE_START_DATE}</b> da boshlanadi. "
        "Qatnashishni tasdiqlang:"
        if is_first_day
        else f"⏰ Eslatma: Challenge <b>{settings.CHALLENGE_START_DATE}</b> da boshlanadi. "
        f"Iltimos, <b>{settings.CONFIRM_WINDOW_END}</b> gacha qatnashishni tasdiqlang:"
    )

    for u in users:
        try:
            await bot.send_message(
                chat_id=u.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=confirm_participation_keyboard(),
            )
        except Exception:
            logger.warning("Tasdiqlash eslatmasi yuborilmadi (tg_id=%s)", u.telegram_id)
        await asyncio.sleep(0.04)


async def _notify_expired_and_promoted(bot: Bot, expired_users: list[User], promoted_list: list[tuple[User, str]]) -> None:
    for u in expired_users:
        if not u.telegram_id:
            continue
        try:
            await bot.send_message(
                chat_id=u.telegram_id,
                text=(
                    "⌛ Afsuski, belgilangan muddat ichida qatnashishni tasdiqlamaganingiz sababli "
                    "o'rningiz kutish ro'yxatidagi ishtirokchiga berildi."
                ),
            )
        except Exception:
            pass
        await asyncio.sleep(0.04)

    for u, otp_plain in promoted_list:
        if not u.telegram_id:
            continue
        try:
            await bot.send_message(
                chat_id=u.telegram_id,
                text=(
                    "🎉 <b>Joy bo'ldi!</b>\n"
                    "Siz kutish ro'yxatidan asosiy ro'yxatga o'tkazildingiz.\n"
                    "⏳ <b>24 soat ichida</b> «✅ Tayyorman» tugmasini bosing, aks holda joy keyingisiga o'tadi."
                ),
                parse_mode="HTML",
                reply_markup=confirm_participation_keyboard(),
            )
            await send_otp_message(bot, u.telegram_id, u.login, otp_plain)
        except Exception:
            logger.warning("Waitlist ko'tarish xabari yuborilmadi (tg_id=%s)", u.telegram_id)
        await asyncio.sleep(0.04)


async def process_confirm_window_close(bot: Bot) -> None:
    today = settings.today_local()
    if today < settings.confirm_window_end_date:
        return

    async with async_session_maker() as db:
        async with db.begin():
            expired_users, promoted_list = await expire_and_promote_waitlist(
                db, expire_initial_registered=True
            )

    if expired_users or promoted_list:
        await _notify_expired_and_promoted(bot, expired_users, promoted_list)


async def process_promoted_waitlist_expiry(bot: Bot) -> None:
    today = settings.today_local()
    if today <= settings.confirm_window_end_date:
        return

    async with async_session_maker() as db:
        async with db.begin():
            expired_users, promoted_list = await expire_and_promote_waitlist(
                db, expire_initial_registered=False
            )

    if expired_users or promoted_list:
        await _notify_expired_and_promoted(bot, expired_users, promoted_list)


async def send_morning_challenge_reminder(bot: Bot) -> None:
    today = settings.today_local()
    if not (settings.challenge_start <= today <= settings.final_date_val):
        return

    async with async_session_maker() as db:
        res = await db.execute(
            select(User.telegram_id).where(
                User.status == "confirmed",
                User.notifications_muted.is_(False),
                User.telegram_id.is_not(None),
            )
        )
        tg_ids = [r[0] for r in res.all()]

    for tg_id in tg_ids:
        try:
            await bot.send_message(
                chat_id=tg_id,
                text=(
                    f"☀️ <b>Bugungi topshiriq ochildi!</b>\n"
                    f"Saytga kirib yechishingiz mumkin: {settings.SITE_URL}\n"
                    "<i>Eslatmalarni o'chirish: /mute</i>"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await asyncio.sleep(0.04)


async def send_evening_challenge_reminder(bot: Bot) -> None:
    today = settings.today_local()
    if not (settings.challenge_start <= today <= settings.final_date_val):
        return

    today_start_local = datetime.combine(today, time.min, tzinfo=settings.tz)
    today_start_utc = today_start_local.astimezone(timezone.utc)

    async with async_session_maker() as db:
        submitted_subq = (
            select(Submission.user_id)
            .where(Submission.submitted_at >= today_start_utc)
            .distinct()
        )
        res = await db.execute(
            select(User.telegram_id).where(
                User.status == "confirmed",
                User.notifications_muted.is_(False),
                User.telegram_id.is_not(None),
                User.id.not_in(submitted_subq),
            )
        )
        tg_ids = [r[0] for r in res.all()]

    for tg_id in tg_ids:
        try:
            await bot.send_message(
                chat_id=tg_id,
                text=(
                    "⏰ <b>Kun yopilishiga 4 soat qoldi!</b>\n"
                    "Bugungi topshiriqni hali topshirmagansiz. Toshkent vaqti bilan 23:59 gacha ulguring!"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await asyncio.sleep(0.04)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)
    scheduler.add_job(
        send_confirmation_reminders,
        trigger="cron",
        hour=10,
        minute=0,
        args=[bot],
        id="bot_confirm_reminders",
        replace_existing=True,
    )
    scheduler.add_job(
        process_confirm_window_close,
        trigger="cron",
        hour=23,
        minute=59,
        args=[bot],
        id="bot_confirm_close",
        replace_existing=True,
    )
    scheduler.add_job(
        process_promoted_waitlist_expiry,
        trigger="interval",
        minutes=15,
        args=[bot],
        id="bot_waitlist_24h_check",
        replace_existing=True,
    )
    scheduler.add_job(
        send_morning_challenge_reminder,
        trigger="cron",
        hour=9,
        minute=0,
        args=[bot],
        id="bot_morning_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        send_evening_challenge_reminder,
        trigger="cron",
        hour=20,
        minute=0,
        args=[bot],
        id="bot_evening_reminder",
        replace_existing=True,
    )
    return scheduler
