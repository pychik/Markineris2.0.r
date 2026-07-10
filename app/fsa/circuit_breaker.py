from __future__ import annotations

import time
from typing import Any

from redis import Redis

from .exceptions import FsaCircuitOpenError

STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_HALF_OPEN = "half_open"


class RedisCircuitBreaker:
    """Redis-backed circuit breaker shared across processes.

    Opens after `failure_threshold` consecutive failures (429s, 5xx, network errors -
    a successful "not found" registry response is a success, not a failure). While open,
    calls are short-circuited for `open_seconds`, doubling on repeated half-open failures
    up to `max_open_seconds`. After the cooldown exactly one caller is let through as a
    half-open trial; if it succeeds the breaker closes, if it fails it reopens.
    """

    _BEFORE_CALL_SCRIPT = """
        local state_key = KEYS[1]
        local trial_key = KEYS[2]
        local now_ms = tonumber(ARGV[1])
        local trial_ttl_ms = tonumber(ARGV[2])

        local state = redis.call('HGET', state_key, 'state')
        local opened_until = tonumber(redis.call('HGET', state_key, 'opened_until') or '0')

        if state == 'open' then
            if now_ms < opened_until then
                return 'open'
            end
            if redis.call('SET', trial_key, '1', 'NX', 'PX', trial_ttl_ms) then
                redis.call('HSET', state_key, 'state', 'half_open')
                return 'trial'
            end
            return 'half_open_busy'
        elseif state == 'half_open' then
            if redis.call('SET', trial_key, '1', 'NX', 'PX', trial_ttl_ms) then
                return 'trial'
            end
            return 'half_open_busy'
        end

        return 'closed'
    """

    _ON_SUCCESS_SCRIPT = """
        local state_key = KEYS[1]
        local trial_key = KEYS[2]
        local base_open_seconds = ARGV[1]

        redis.call('HSET', state_key, 'state', 'closed', 'failures', '0',
            'opened_until', '0', 'backoff_seconds', base_open_seconds)
        redis.call('DEL', trial_key)
    """

    _ON_FAILURE_SCRIPT = """
        local state_key = KEYS[1]
        local trial_key = KEYS[2]
        local now_ms = tonumber(ARGV[1])
        local threshold = tonumber(ARGV[2])
        local base_open_seconds = tonumber(ARGV[3])
        local max_open_seconds = tonumber(ARGV[4])

        redis.call('DEL', trial_key)
        local state = redis.call('HGET', state_key, 'state')

        if state == 'half_open' then
            local backoff = tonumber(redis.call('HGET', state_key, 'backoff_seconds')) or base_open_seconds
            local new_backoff = math.min(backoff * 2, max_open_seconds)
            redis.call('HSET', state_key, 'state', 'open',
                'opened_until', now_ms + (new_backoff * 1000), 'backoff_seconds', new_backoff)
            return 'reopened'
        end

        local failures = redis.call('HINCRBY', state_key, 'failures', 1)

        if failures >= threshold then
            redis.call('HSET', state_key, 'state', 'open',
                'opened_until', now_ms + (base_open_seconds * 1000), 'backoff_seconds', base_open_seconds)
            return 'opened'
        end

        return 'closed'
    """

    def __init__(
        self,
        *,
        redis_client: Redis,
        state_key: str,
        failure_threshold: int,
        open_seconds: int,
        max_open_seconds: int,
        trial_ttl_seconds: float,
    ) -> None:
        self.redis = redis_client
        self.state_key = state_key
        self.trial_key = f"{state_key}:trial"
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self.max_open_seconds = max_open_seconds
        self.trial_ttl_ms = max(int(trial_ttl_seconds * 1000), 1)

        self._before_call = self.redis.register_script(self._BEFORE_CALL_SCRIPT)
        self._on_success_script = self.redis.register_script(self._ON_SUCCESS_SCRIPT)
        self._on_failure_script = self.redis.register_script(self._ON_FAILURE_SCRIPT)

    def before_call(self) -> None:
        now_ms = int(time.time() * 1000)
        result = self._before_call(
            keys=[self.state_key, self.trial_key],
            args=[now_ms, self.trial_ttl_ms],
        )
        result = result.decode() if isinstance(result, bytes) else result

        if result in ("open", "half_open_busy"):
            raise FsaCircuitOpenError("Проверка временно недоступна: слишком много ошибок ФСА подряд")

    def on_success(self) -> None:
        self._on_success_script(keys=[self.state_key, self.trial_key], args=[self.open_seconds])

    def on_failure(self) -> None:
        now_ms = int(time.time() * 1000)
        self._on_failure_script(
            keys=[self.state_key, self.trial_key],
            args=[now_ms, self.failure_threshold, self.open_seconds, self.max_open_seconds],
        )

    def get_state(self) -> dict[str, Any]:
        raw = self.redis.hgetall(self.state_key)
        data = {
            (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
            for k, v in raw.items()
        }
        return {
            "state": data.get("state", STATE_CLOSED),
            "failures": int(data.get("failures", 0)),
            "opened_until": int(data.get("opened_until", 0)),
        }
