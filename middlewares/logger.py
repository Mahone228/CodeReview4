from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
import asyncio

from storage.database import Database

class ActionLoggerMiddleware(BaseMiddleware):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        
        user_id = None
        username = None
        action_type = "unknown"
        text = ""

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            username = event.from_user.username if event.from_user else None
            action_type = "message"
            text = event.text or ""
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            username = event.from_user.username
            action_type = "callback_query"
            text = event.data or ""
            
        if user_id:
            asyncio.create_task(self.db.log_action(user_id, username, action_type, text))

        return await handler(event, data)
