from redis import Redis, ConnectionPool

from config import settings


TG_DATABASE_REDIS_CONNECTION_POOL = ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_TG_NOTIFY_DB_NUMBER,
)

conn = Redis.from_url(settings.REDIS_CONN)
tg_redis_database_connection = Redis(connection_pool=TG_DATABASE_REDIS_CONNECTION_POOL)