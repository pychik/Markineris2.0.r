from typing import Any, Awaitable, Callable, AsyncGenerator

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.gateways.db.repositories.user import UserRepository
from src.service.user import UserService


class UserServiceMiddleware(BaseMiddleware):
    def __init__(self, pool: async_sessionmaker[AsyncSession]) -> None:
        super().__init__()
        self._pool = pool

    async def _get_session(self) -> AsyncGenerator[AsyncSession, Any]:
        async with self._pool() as session:
            yield session

    @staticmethod
    def _get_user_repository(session: AsyncSession) -> UserRepository:
        return UserRepository(session=session)

    @staticmethod
    def _get_user_service(repo: UserRepository) -> UserService:
        return UserService(repo=repo)

    async def __call__(
        self,
        handle: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async for session in self._get_session():
            async with session.begin():
                repo = self._get_user_repository(session=session)
                service = self._get_user_service(repo=repo)

                data['user_service'] = service

                return await handle(event, data)
