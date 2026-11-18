import html
from typing import Iterable

from aiogram.types import Message

from app.core.config import settings

MAX_TG_LEN = 4096

LEVEL_OPTIONS = [
    ("Yangi boshlovchi", "beginner"),
    ("Ozgina bilaman", "basic"),
    ("O'rta", "intermediate"),
    ("Ilg'or", "advanced"),
]

AGE_OPTIONS = [
    ("Maktab o'quvchisi", "school"),
    ("Talaba", "student"),
    ("Ishlayman", "working"),
    ("Boshqa", "other"),
]

REGION_OPTIONS = [
    "Toshkent shahri",
    "Toshkent v.",
    "Samarqand",
    "Buxoro",
    "Andijon",
    "Farg'ona",
    "Namangan",
    "Qashqadaryo",
    "Surxondaryo",
    "Xorazm",
    "Navoiy",
    "Jizzax",
    "Sirdaryo",
    "Qoraqalpog'iston",
    "Xorijda",
]

SOURCE_OPTIONS = [
    "Telegram",
    "Instagram",
    "Do'stlar",
    "Universitet-maktab",
    "Boshqa",
]

INTEREST_OPTIONS = [
    "Web",
    "Data va AI",
    "Telegram botlar",
    "Mobil",
    "Boshqa",
]

STATUS_LABELS = {
    "registered": "Ro'yxatdan o'tgan (tasdiqlash kutilmoqda)",
    "waitlist": "Kutish ro'yxatida",
    "confirmed": "Tasdiqlangan (faol ishtirokchi)",
    "expired": "Tasdiqlash muddati tugagan",
    "disqualified": "Diskvalifikatsiya qilingan",
    "banned": "Bloklangan",
}


def escape_html(value: object) -> str:
    return html.escape(str(value or ""), quote=False)


def get_rules_text() -> str:
    return (
        f"📋 <b>PyChallenge Qoidalari (v{settings.RULES_VERSION})</b>\n\n"
        "1. Musobaqa Python dasturlash tili bo'yicha 30 kunlik challenge shaklida o'tkaziladi.\n"
        f"2. Challenge boshlanish sanasi: <b>{settings.CHALLENGE_START_DATE}</b>. "
        f"Har kuni yangi topshiriq Toshkent vaqti bilan <b>00:00</b> da ochiladi.\n"
        f"3. Asosiy ishtirokchilar soni: <b>{settings.MAX_PARTICIPANTS}</b> nafar. "
        "Joy to'lgandan keyin ro'yxatdan o'tganlar kutish ro'yxatiga tushadi.\n"
        f"4. Qatnashishni tasdiqlash oynasi: <b>{settings.CONFIRM_WINDOW_START}</b> dan "
        f"<b>{settings.CONFIRM_WINDOW_END}</b> gacha. Shu muddatda tasdiqlamaganlar o'rniga "
        "kutish ro'yxatidagi ishtirokchilar taklif qilinadi.\n"
        "5. Har bir kunlik topshiriqni belgilangan vaqt ichida mustaqil bajarish shart. "
        "Ko'chirish, boshqa tabga o'tish va anti-cheat qoidalarini buzish diskvalifikatsiyaga olib keladi.\n"
        "6. Mukofot olish uchun ro'yxatdan o'tishda kiritilgan ism-familiya bank kartasi egasining ismi bilan "
        "mos bo'lishi shart.\n"
        "7. Tashkilotchilar qoidalarni buzgan ishtirokchini musobaqadan chetlashtirish huquqiga ega."
    )


def split_message(text: str, max_len: int = MAX_TG_LEN) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_len:
        split_at = remaining.rfind("\n", 0, max_len)
        if split_at <= 0:
            split_at = max_len
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks


async def send_long_message(message: Message, text: str, **kwargs) -> Message:
    parts = split_message(text)
    last_msg = None
    for idx, part in enumerate(parts):
        if idx == len(parts) - 1:
            last_msg = await message.answer(part, **kwargs)
        else:
            last_msg = await message.answer(part, parse_mode=kwargs.get("parse_mode"))
    return last_msg
