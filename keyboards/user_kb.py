"""Клавиатуры для обычных пользователей."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def subscribe_kb(channel_url: str | None, code: str | None) -> InlineKeyboardMarkup:
    rows = []
    if channel_url:
        rows.append([InlineKeyboardButton(text="📢 Подписаться на канал", url=channel_url)])
    # callback_data: «chk:<код>» (до 64 байт; «-» если кода нет)
    rows.append([InlineKeyboardButton(text="✅ Я подписался", callback_data=f"chk:{code or '-'}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
