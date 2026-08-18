from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from redis import Redis

from config import settings
from redis_queue.redis_instance import get_redis_client

from .constants import (
    JOB_STATUS_DONE,
    JOB_STATUS_ERROR,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_QUEUED,
    REDIS_KEY_JOB_PREFIX,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RdCheckJobStore:
    """Ephemeral (Redis-only, TTL-bound) status store for RD check jobs, polled by the admin page."""

    def __init__(self, *, redis_client: Redis | None = None, ttl_seconds: int | None = None) -> None:
        self.redis = redis_client or get_redis_client()
        self.ttl_seconds = ttl_seconds or settings.FSA_JOB_RESULT_TTL

    def create(self, *, request_id: str, doc_type: str, number: str, **extra: Any) -> None:
        now = _now_iso()
        self._save(
            request_id,
            {
                "status": JOB_STATUS_QUEUED,
                "doc_type": doc_type,
                "number": number,
                "created_at": now,
                "updated_at": now,
                **extra,
            },
        )

    def mark_processing(self, request_id: str) -> None:
        self._update(request_id, status=JOB_STATUS_PROCESSING)

    def mark_done(self, request_id: str, result: dict[str, Any]) -> None:
        self._update(request_id, status=JOB_STATUS_DONE, result=result)

    def mark_error(self, request_id: str, message: str) -> None:
        self._update(request_id, status=JOB_STATUS_ERROR, error=message)

    def get(self, request_id: str) -> dict[str, Any] | None:
        raw = self.redis.get(self._key(request_id))
        if not raw:
            return None
        return json.loads(raw)

    def _key(self, request_id: str) -> str:
        return f"{REDIS_KEY_JOB_PREFIX}:{request_id}"

    def _save(self, request_id: str, payload: dict[str, Any]) -> None:
        self.redis.set(self._key(request_id), json.dumps(payload), ex=self.ttl_seconds)

    def _update(self, request_id: str, **fields: Any) -> None:
        data = self.get(request_id) or {}
        data.update(fields)
        data["updated_at"] = _now_iso()
        self._save(request_id, data)
