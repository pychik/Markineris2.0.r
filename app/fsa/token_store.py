from __future__ import annotations

import base64
import json
import time
import uuid
from typing import Callable

from redis import Redis

LOCK_TTL_MS = 15_000
LOCK_WAIT_STEP_SEC = 0.25
LOCK_WAIT_MAX_STEPS = 40
TOKEN_EXPIRY_SAFETY_MARGIN_SEC = 30


def _decode_jwt_expiry(token: str) -> int | None:
    """Best-effort extraction of the `exp` claim from a bearer/JWT token, without a JWT dependency."""
    try:
        raw = token.split(" ", 1)[-1]
        payload_segment = raw.split(".")[1]
        padding = "=" * (-len(payload_segment) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_segment + padding))
        exp = payload.get("exp")
        return int(exp) if exp else None
    except Exception:
        return None


class FsaTokenStore:
    """Caches the anonymous auth token in Redis so /login is not called on every check,
    which would otherwise burn part of the already tight per-IP rate limit budget."""

    def __init__(self, *, redis_client: Redis, key: str, lock_key: str, default_ttl_seconds: int) -> None:
        self.redis = redis_client
        self.key = key
        self.lock_key = lock_key
        self.default_ttl_seconds = default_ttl_seconds

    def get_token(self, *, login_fn: Callable[[], str]) -> str:
        cached = self.redis.get(self.key)
        if cached:
            return cached.decode() if isinstance(cached, bytes) else cached

        return self._refresh(login_fn)

    def invalidate(self) -> None:
        self.redis.delete(self.key)

    def _refresh(self, login_fn: Callable[[], str]) -> str:
        lock_value = uuid.uuid4().hex
        acquired = self.redis.set(self.lock_key, lock_value, nx=True, px=LOCK_TTL_MS)

        if not acquired:
            for _ in range(LOCK_WAIT_MAX_STEPS):
                time.sleep(LOCK_WAIT_STEP_SEC)
                cached = self.redis.get(self.key)
                if cached:
                    return cached.decode() if isinstance(cached, bytes) else cached
            # lock holder didn't finish in time - fetch a token ourselves rather than deadlock

        try:
            token = login_fn()
            ttl = self._resolve_ttl(token)
            self.redis.set(self.key, token, ex=ttl)
            return token
        finally:
            if acquired:
                self.redis.delete(self.lock_key)

    def _resolve_ttl(self, token: str) -> int:
        exp = _decode_jwt_expiry(token)
        if not exp:
            return self.default_ttl_seconds

        remaining = int(exp - time.time()) - TOKEN_EXPIRY_SAFETY_MARGIN_SEC
        if remaining <= 0:
            return self.default_ttl_seconds

        return min(remaining, self.default_ttl_seconds)
