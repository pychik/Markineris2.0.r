import asyncio
import logging

from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.methods import DeleteWebhook

from src.core.config import settings
from src.core.middlewares.base_client import AsyncClientMiddleware
from src.core.middlewares.user_schema import UserSchemaMiddleware
from src.core.middlewares.user_service import UserServiceMiddleware
from src.gateways.db.connection import get_async_session_maker, get_async_engine
from src.gateways.redis.connection import get_async_redis_client
from src.handlers import command, verification, unknown_command, account_refill_balance, bonus_code
from src.infrastructure.client import get_base_client
from src.init_bot import bot
from src.keyboards.menu import add_menu_commands

logging.basicConfig(level=logging.INFO)


def create_dispatcher(storage: RedisStorage) -> Dispatcher:
    dp = Dispatcher(storage=storage)

    async_engine = get_async_engine(settings.database_url)
    pool = get_async_session_maker(engine=async_engine)
    async_client = get_base_client()

    dp.message.outer_middleware(UserServiceMiddleware(pool))
    dp.message.middleware(UserSchemaMiddleware())
    dp.message.middleware(AsyncClientMiddleware(async_client))

    dp.callback_query.outer_middleware(UserServiceMiddleware(pool))
    dp.callback_query.middleware(UserSchemaMiddleware())
    dp.callback_query.middleware(AsyncClientMiddleware(async_client))

    dp.include_router(router=command.router)
    dp.include_router(router=verification.router)
    dp.include_router(router=account_refill_balance.router)
    dp.include_router(router=bonus_code.router)
    dp.include_router(router=unknown_command.router)

    return dp


async def main() -> None:
    storage = RedisStorage(await get_async_redis_client(db_number=settings.REDIS_BOT_STORAGE_DB))

    dp = create_dispatcher(storage)

    await add_menu_commands(bot)

    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
