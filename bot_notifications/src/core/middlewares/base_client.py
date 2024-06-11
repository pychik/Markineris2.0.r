from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.infrastructure.client import BaseClient


class AsyncClientMiddleware(BaseMiddleware):
    def __init__(self, client: BaseClient) -> None:
        super().__init__()
        self.client = client

    async def __call__(
        self,
        handle: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data['client'] = self.client
        return await handle(event, data)
