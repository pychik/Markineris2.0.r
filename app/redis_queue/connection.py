from redis import Redis

from config import settings

conn = Redis.from_url(settings.REDIS_CONN)