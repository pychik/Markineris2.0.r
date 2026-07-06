from __future__ import annotations

import time

from redis import Redis

from .exceptions import FsaRateLimitedError


class RedisRateLimiter:
    """Global leaky-bucket pacing shared across processes via Redis.

    Every caller atomically reserves the next free slot spaced `interval_ms` apart
    from the previous one (classic virtual-scheduling rate limiter). This keeps the
    outbound request rate to a hard upstream limit regardless of how many app/worker
    processes call it concurrently.
    """

    _RESERVE_SLOT_SCRIPT = """
        local key = KEYS[1]
        local interval_ms = tonumber(ARGV[1])
        local now_ms = tonumber(ARGV[2])
        local ttl_ms = tonumber(ARGV[3])

        local last = tonumber(redis.call('GET', key))
        if last == nil or last < now_ms then
            last = now_ms
        end

        local wait_ms = last - now_ms
        redis.call('SET', key, last + interval_ms, 'PX', ttl_ms)
        return wait_ms
    """

    def __init__(self, *, redis_client: Redis, key: str, rps: float, max_wait_seconds: float) -> None:
        self.redis = redis_client
        self.key = key
        self.interval_ms = max(int(1000 / rps), 1)
        self.max_wait_ms = max(int(max_wait_seconds * 1000), 0)
        self._script = self.redis.register_script(self._RESERVE_SLOT_SCRIPT)

    def acquire(self) -> None:
        now_ms = int(time.time() * 1000)
        ttl_ms = self.max_wait_ms + self.interval_ms + 5000

        wait_ms = int(self._script(keys=[self.key], args=[self.interval_ms, now_ms, ttl_ms]))

        if wait_ms > self.max_wait_ms:
            raise FsaRateLimitedError(
                f"Превышено время ожидания слота для запроса к ФСА ({wait_ms}мс > {self.max_wait_ms}мс)"
            )

        if wait_ms > 0:
            time.sleep(wait_ms / 1000)
