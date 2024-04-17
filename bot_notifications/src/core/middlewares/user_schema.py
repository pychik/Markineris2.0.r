from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from src.schemas.user import TgUserSchema


class UserSchemaMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()
        self._schema = TgUserSchema

    def _create_user_schema(self, user: User) -> TgUserSchema:
        return self._schema.create(user)

    async def __call__(
        self,
        handle: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:

        data['tg_user_schema'] = self._create_user_schema(event.from_user)

        return await handle(event, data)
