from redis.client import Redis

from config import settings

CACHE_DB_NUMBER = 2

def get_redis_client():
    return Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=CACHE_DB_NUMBER)
