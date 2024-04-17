from redis.asyncio import Redis

from src.core.config import settings


async def get_async_redis_client(db_number: int) -> Redis:
    return Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=db_number)
