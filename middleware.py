from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
import os

class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        allowed_ids_raw = os.getenv("ALLOWED_IDS", "")
        allowed_ids = [int(i.strip()) for i in allowed_ids_raw.split(",") if i.strip()]
        # Перевірка: чи є відправник адміном
        if event.from_user.id not in allowed_ids:
            await event.answer("🚫 Доступ заборонено. Ви не авторизовані для керування цим ботом.")
            return # Зупиняємо виконання (handler не викликається)
        
        return await handler(event, data)