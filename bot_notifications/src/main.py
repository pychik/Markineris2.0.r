import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

from aiogram import Dispatcher
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.methods import DeleteWebhook
from aiogram.utils.backoff import BackoffConfig
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.config import settings
from src.core.middlewares.base_client import AsyncClientMiddleware
from src.core.middlewares.user_schema import UserSchemaMiddleware
from src.core.middlewares.user_service import UserServiceMiddleware
from src.gateways.db.connection import get_async_session_maker, get_async_engine
from src.gateways.redis.connection import get_async_redis_client
from src.handlers import command, verification, unknown_command, account_refill_balance, bonus_code
from src.infrastructure.client import BaseClient, get_base_client
from src.infrastructure.logger import logger
from src.init_bot import bot
from src.keyboards.menu import add_menu_commands

logging.basicConfig(level=logging.INFO)


def create_dispatcher(storage: RedisStorage) -> tuple[Dispatcher, BaseClient, AsyncEngine]:
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

    return dp, async_client, async_engine

async def run_telegram_startup_step(
        step_name: str,
        action: Callable[[], Awaitable[object]],
) -> None:
    delay = settings.TELEGRAM_STARTUP_RETRY_DELAY_SEC
    attempts = settings.TELEGRAM_STARTUP_RETRIES

    for attempt in range(1, attempts + 1):
        try:
            await action()
            if attempt > 1:
                logger.info("Шаг '{}' выполнен с {} попытки", step_name, attempt)
            return
        except (TelegramNetworkError, TelegramAPIError) as exc:
            if attempt == attempts:
                logger.warning(
                    "Шаг '{}' не выполнен после {} попыток: {}",
                    step_name,
                    attempts,
                    exc,
                )
                return

            logger.warning(
                "Ошибка на шаге '{}' ({}/{}): {}. Повтор через {:.1f}с",
                step_name,
                attempt,
                attempts,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
            delay = min(
                delay * settings.TELEGRAM_BACKOFF_FACTOR,
                settings.TELEGRAM_BACKOFF_MAX_DELAY_SEC,
            )

async def shutdown_resources(
        storage: RedisStorage,
        async_client: BaseClient,
        async_engine: AsyncEngine,
) -> None:
    with contextlib.suppress(Exception):
        await async_client.close()

    with contextlib.suppress(Exception):
        await storage.close()

    with contextlib.suppress(Exception):
        await bot.session.close()

    with contextlib.suppress(Exception):
        await async_engine.dispose()


async def main() -> None:
    storage = RedisStorage(await get_async_redis_client(db_number=settings.REDIS_BOT_STORAGE_DB))
    dp, async_client, async_engine = create_dispatcher(storage)

    polling_backoff = BackoffConfig(
        min_delay=settings.TELEGRAM_BACKOFF_MIN_DELAY_SEC,
        max_delay=settings.TELEGRAM_BACKOFF_MAX_DELAY_SEC,
        factor=settings.TELEGRAM_BACKOFF_FACTOR,
        jitter=settings.TELEGRAM_BACKOFF_JITTER,
    )
    try:
        await run_telegram_startup_step(
            step_name="set_my_commands",
            action=lambda: add_menu_commands(bot),
        )
        await run_telegram_startup_step(
            step_name="delete_webhook",
            action=lambda: bot(
                DeleteWebhook(
                    drop_pending_updates=settings.TELEGRAM_DROP_PENDING_UPDATES_ON_STARTUP,
                )
            ),
        )

        await dp.start_polling(
            bot,
            polling_timeout=settings.TELEGRAM_POLLING_TIMEOUT_SEC,
            backoff_config=polling_backoff,
            close_bot_session=False,
        )
    finally:
        await shutdown_resources(
            storage=storage,
            async_client=async_client,
            async_engine=async_engine,
        )



if __name__ == '__main__':
    asyncio.run(main())
