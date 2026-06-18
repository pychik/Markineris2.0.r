import time

import requests
from flask import jsonify, request

from config import settings
from logger import logger

DADATA_SUGGEST_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"
DADATA_MIN_QUERY_LEN = 7
DADATA_TIMEOUT = (1.5, 3.0)
DADATA_CACHE_TTL_SEC = 300
DADATA_UPSTREAM_COOLDOWN_SEC = 60

_dadata_cache = {}
_dadata_blocked_until = 0.0


def _dadata_normalize_query(raw_query: str) -> str:
    return "".join(ch for ch in raw_query if ch.isdigit())


def _dadata_get_cached_items(query: str):
    cached = _dadata_cache.get(query)
    if not cached:
        return None

    expires_at, items = cached
    now = time.monotonic()
    if expires_at <= now:
        _dadata_cache.pop(query, None)
        return None

    return items


def _dadata_set_cached_items(query: str, items: list) -> None:
    _dadata_cache[query] = (time.monotonic() + DADATA_CACHE_TTL_SEC, items)


def _dadata_set_cooldown() -> None:
    global _dadata_blocked_until
    _dadata_blocked_until = time.monotonic() + DADATA_UPSTREAM_COOLDOWN_SEC


def _dadata_is_in_cooldown() -> bool:
    return _dadata_blocked_until > time.monotonic()


def _dadata_build_items(data: dict) -> list:
    items = []
    for suggestion in data.get("suggestions", []):
        item_data = suggestion.get("data") or {}
        state = item_data.get("state") or {}
        items.append({
            "inn": item_data.get("inn"),
            "kpp": item_data.get("kpp"),
            "opf": (item_data.get("opf") or {}).get("short"),
            "name": (item_data.get("name") or {}).get("full") or suggestion.get("value"),
            "address": (item_data.get("address") or {}).get("value"),
            "status": state.get("status"),
        })
    return items


def h_dadata_party_by_inn():
    q = _dadata_normalize_query((request.args.get("q") or "").strip())
    if len(q) < DADATA_MIN_QUERY_LEN:
        return jsonify({"ok": True, "items": []})

    if _dadata_is_in_cooldown():
        return jsonify({"ok": False, "error": "dadata_temporarily_unavailable", "items": []}), 503

    cached_items = _dadata_get_cached_items(q)
    if cached_items is not None:
        return jsonify({"ok": True, "items": cached_items})

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Token {settings.DADATA_TOKEN}",
    }
    body = {
        "query": q,
        "count": 7,
    }

    try:
        response = requests.post(
            DADATA_SUGGEST_URL,
            headers=headers,
            json=body,
            timeout=DADATA_TIMEOUT,
        )
    except requests.Timeout:
        logger.warning("DaData suggest timeout q=%s ip=%s", q, request.remote_addr)
        return jsonify({"ok": False, "error": "timeout", "items": []}), 504
    except requests.RequestException:
        logger.exception("DaData suggest request failed q=%s ip=%s", q, request.remote_addr)
        return jsonify({"ok": False, "error": "dadata_unavailable", "items": []}), 502

    if response.status_code == 400:
        logger.warning("DaData suggest bad request q=%s ip=%s", q, request.remote_addr)
        return jsonify({"ok": False, "error": "dadata_bad_request", "items": []}), 502

    if response.status_code in {401, 403, 429} or response.status_code >= 500:
        _dadata_set_cooldown()
        logger.warning(
            "DaData suggest upstream rejected status=%s q=%s ip=%s",
            response.status_code,
            q,
            request.remote_addr,
        )
        return jsonify({"ok": False, "error": "dadata_temporarily_unavailable", "items": []}), 503

    try:
        response.raise_for_status()
        data = response.json()
    except ValueError:
        logger.exception("DaData suggest returned invalid json q=%s ip=%s", q, request.remote_addr)
        _dadata_set_cooldown()
        return jsonify({"ok": False, "error": "dadata_invalid_response", "items": []}), 502
    except requests.RequestException:
        logger.exception("DaData suggest failed after response q=%s ip=%s", q, request.remote_addr)
        return jsonify({"ok": False, "error": "dadata_unavailable", "items": []}), 502

    items = _dadata_build_items(data)
    _dadata_set_cached_items(q, items)
    return jsonify({"ok": True, "items": items})
