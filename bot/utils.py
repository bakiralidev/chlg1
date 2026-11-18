import asyncio
import logging
import re

from aiogram import Bot
from aiogram.types import Message

from app.core.config import settings
from bot.texts import escape_html

logger = logging.getLogger(__name__)


def normalize_uz_phone(raw_phone: str) -> str | None:
    """Normalize phone number and ensure it starts with +998 and has 9 local digits."""
    digits = re.sub(r"\D", "", raw_phone or "")
    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"
    return None


async def delete_message_after_delay(bot: Bot, chat_id: int, message_id: int, delay_secs: int = 60) -> None:
    await asyncio.sleep(delay_secs)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        logger.debug("OTP xabarini o'chirib bo'lmadi (chat_id=%s)", chat_id)


async def send_otp_message(bot: Bot, chat_id: int, login: str, otp_plain: str, prefix: str = "") -> None:
    """Send login + one-time password and schedule auto-deletion in 60 seconds."""
    text = (
        f"{prefix}"
        f"🔐 <b>Kirish ma'lumotlaringiz:</b>\n\n"
        f"Loginingiz: <code>{escape_html(login)}</code>\n"
        f"Bir martalik parol: <code>{escape_html(otp_plain)}</code>\n\n"
        f"🌐 Saytga kiring: {escape_html(settings.SITE_URL)}\n"
        f"Birinchi kirishda yangi parol o'rnatasiz.\n"
        f"⏳ Parol {settings.OTP_TTL_MINUTES} daqiqa amal qiladi.\n\n"
        f"⚠️ <b>Parolni ko'chirib oling, bu xabar 60 soniyadan keyin avtomatik o'chadi!</b>"
    )
    sent: Message = await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    asyncio.create_task(delete_message_after_delay(bot, chat_id, sent.message_id, delay_secs=60))
