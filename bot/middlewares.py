import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class PrivateChatOnlyMiddleware(BaseMiddleware):
    """Ignore all updates that do not originate from a private chat."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        chat = None
        if isinstance(event, Message):
            chat = event.chat
        elif isinstance(event, CallbackQuery) and event.message:
            chat = event.message.chat

        if chat is not None and chat.type != "private":
            return None

        return await handler(event, data)


class FloodControlMiddleware(BaseMiddleware):
    """Simple per-user rate limiter to prevent rapid button/command spam."""

    def __init__(self, min_interval_secs: float = 0.6) -> None:
        self.min_interval = min_interval_secs
        self._last_seen: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is not None:
            now = time.monotonic()
            last = self._last_seen.get(user.id, 0.0)
            if now - last < self.min_interval:
                if isinstance(event, CallbackQuery):
                    await event.answer("Biroz kuting...", show_alert=False)
                return None
            self._last_seen[user.id] = now

        return await handler(event, data)
