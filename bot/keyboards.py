from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.texts import (
    AGE_OPTIONS,
    INTEREST_OPTIONS,
    LEVEL_OPTIONS,
    REGION_OPTIONS,
    SOURCE_OPTIONS,
)

BTN_RESET_PASSWORD = "🔑 Parolni tiklash"
BTN_MY_RESULTS = "📊 Mening natijam"
BTN_RULES = "📋 Qoidalar"
BTN_CONTACT_ADMIN = "📩 Adminga yozish"
BTN_MY_STATUS = "ℹ️ Mening holatim"
BTN_CANCEL = "❌ Bekor qilish"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_RESET_PASSWORD), KeyboardButton(text=BTN_MY_RESULTS)],
            [KeyboardButton(text=BTN_RULES), KeyboardButton(text=BTN_MY_STATUS)],
            [KeyboardButton(text=BTN_CONTACT_ADMIN)],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Raqamni ulashish", request_contact=True)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Roziman", callback_data="consent:agree"),
                InlineKeyboardButton(text="❌ Rozi emasman", callback_data="consent:decline"),
            ]
        ]
    )


def confirm_participation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tayyorman", callback_data="confirm_participation")]
        ]
    )


def contact_admin_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 Adminga yozish", callback_data="open_support")]
        ]
    )


def survey_level_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for label, code in LEVEL_OPTIONS:
        builder.button(text=label, callback_data=f"survey_level:{code}")
    builder.button(text=BTN_CANCEL, callback_data="survey_cancel")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def survey_age_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for label, code in AGE_OPTIONS:
        builder.button(text=label, callback_data=f"survey_age:{code}")
    builder.button(text=BTN_CANCEL, callback_data="survey_cancel")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def survey_region_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, region in enumerate(REGION_OPTIONS):
        builder.button(text=region, callback_data=f"survey_region:{idx}")
    builder.button(text=BTN_CANCEL, callback_data="survey_cancel")
    builder.adjust(2)
    return builder.as_markup()


def survey_source_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, src in enumerate(SOURCE_OPTIONS):
        builder.button(text=src, callback_data=f"survey_source:{idx}")
    builder.button(text=BTN_CANCEL, callback_data="survey_cancel")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def survey_interest_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, item in enumerate(INTEREST_OPTIONS):
        builder.button(text=item, callback_data=f"survey_interest:{idx}")
    builder.button(text=BTN_CANCEL, callback_data="survey_cancel")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()
