import asyncio

from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.methods import DeleteWebhook

from src.gateways.redis.connection import get_async_redis_client
from src.core.config import settings
from src.core.middlewares.user_schema import UserSchemaMiddleware
from src.core.middlewares.user_service import UserServiceMiddleware
from src.gateways.db.connection import get_async_session_maker, get_async_engine
from src.handlers import command, user, unknown_command
from src.init_bot import bot
from src.keyboards.menu import add_menu_commands


def create_dispatcher(storage: RedisStorage) -> Dispatcher:
    dp = Dispatcher(storage=storage)

    async_engine = get_async_engine(settings.database_url)
    pool = get_async_session_maker(engine=async_engine)

    dp.message.middleware(UserServiceMiddleware(pool))
    dp.message.middleware(UserSchemaMiddleware())

    dp.callback_query.middleware(UserServiceMiddleware(pool))
    dp.callback_query.middleware(UserSchemaMiddleware())

    dp.include_router(router=command.router)
    dp.include_router(router=user.router)
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
