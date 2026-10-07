"""Tezaurus shuffle queue for local companies, with state stored in Redis."""

import json
import random
from typing import Any

from redis import Redis, WatchError

from config import settings

from .repository import LocalTezaurusRepository


class LocalProcessingCompanySelector:
    def __init__(self, *, redis_client: Redis | None = None) -> None:
        self.redis = redis_client if redis_client is not None else Redis.from_url(settings.REDIS_CONN)
        self.repository = LocalTezaurusRepository()

    def _candidates(self, category: str, origin: str) -> list[dict[str, Any]]:
        companies = self.repository.get_processing_companies()
        return sorted(
            (
                company for company in companies
                if company.get("is_active") is True
                and category in (company.get("categories") or [])
                and origin in (company.get("origins") or [])
            ),
            key=lambda company: int(company["external_id"]),
        )

    def select(self, *, category: str, origin: str) -> dict[str, Any]:
        criteria = {"category": category, "origin": origin}
        candidates = self._candidates(category, origin)
        if not candidates:
            return {
                "ok": False,
                "matched": False,
                "message": "Для категории и происхождения не настроена включенная компания-обработчик.",
                "criteria": criteria,
                "company": None,
            }

        candidate_ids = [company["external_id"] for company in candidates]
        companies_by_id = {company["external_id"]: company for company in candidates}
        key = f"tezaurus_fallback:processing_companies:selection:{category}:{origin}"

        while True:
            with self.redis.pipeline() as pipe:
                try:
                    pipe.watch(key)
                    raw = pipe.get(key)
                    try:
                        state = json.loads(raw) if raw else {}
                    except (TypeError, ValueError):
                        state = {}
                    if not isinstance(state, dict):
                        state = {}

                    queue = list(state.get("queue_company_ids") or [])
                    position = int(state.get("queue_position") or 0)
                    rebuilt = (
                        state.get("candidate_company_ids") != candidate_ids
                        or position < 0
                        or position >= len(queue)
                        or any(company_id not in companies_by_id for company_id in queue)
                    )
                    if rebuilt:
                        queue = list(candidate_ids)
                        random.shuffle(queue)
                        if len(queue) > 1 and queue[0] == state.get("last_company_id"):
                            queue = queue[1:] + queue[:1]
                        position = 0

                    selected_id = queue[position]
                    next_state = {
                        "candidate_company_ids": candidate_ids,
                        "queue_company_ids": queue,
                        "queue_position": position + 1,
                        "last_company_id": selected_id,
                        "cycle_no": int(state.get("cycle_no") or 0) + int(rebuilt),
                    }
                    pipe.multi()
                    pipe.set(key, json.dumps(next_state, ensure_ascii=False))
                    pipe.execute()
                    break
                except WatchError:
                    continue

        selected = companies_by_id[selected_id]
        return {
            "ok": True,
            "matched": True,
            "criteria": criteria,
            "company": {
                "id": int(selected["external_id"]),
                "title": selected["title"],
                "inn": selected["inn"],
                "is_active": True,
                "allowed_categories": selected["categories"],
                "allowed_origins": selected["origins"],
            },
            "selection": {
                "mode": "shuffle_queue",
                "cycle_no": next_state["cycle_no"],
                "cycle_position": next_state["queue_position"],
                "cycle_size": len(queue),
                "queue_rebuilt": rebuilt,
            },
        }

    def select_batch(self, items: list[dict[str, str]]) -> dict[str, Any]:
        results = []
        for item in items:
            result = self.select(category=item["category"], origin=item["origin"])
            if result["ok"] is False:
                result["status_code"] = 409
            results.append({"client_id": item["client_id"], **result})
        return {"ok": True, "items": results}
