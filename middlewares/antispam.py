import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message

class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 1.0):
        super().__init__()
        self.limit = limit
        self.caches = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        
        if not isinstance(event, Message):
            return await handler(event, data)
            
        user_id = event.from_user.id
        now = time.time()
        
        last_time = self.caches.get(user_id, 0)
        
        if now - last_time < self.limit:
            return
            
        self.caches[user_id] = now
        return await handler(event, data)
