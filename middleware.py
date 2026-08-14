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
        admin_id = int(os.getenv("ADMIN_ID"))
        allowed_ids = [int(i.strip()) for i in os.getenv("ALLOWED_IDS", "").split(",") if i.strip()]
        # Перевірка: чи є відправник адміном
        if event.from_user.id not in allowed_ids:
            await event.answer("🚫 Доступ заборонено. Ви не авторизовані для керування цим ботом.")
            return # Зупиняємо виконання (handler не викликається)
        
        return await handler(event, data)