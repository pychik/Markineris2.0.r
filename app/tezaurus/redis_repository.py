from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from redis import Redis

from config import settings
from logger import logger

from .constants import (
    DICTIONARY_COLORS,
    DICTIONARY_COUNTRIES,
    DICTIONARY_TNVED,
)
from .exceptions import TezaurusStorageError
from .key_builder import (
    normalize_countries_category,
    normalize_key_part,
    normalize_tnved_category,
    normalize_tnved_gender,
    normalize_tnved_subcategory,
)


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class RedisTezaurusRepository:
    """Redis persistence for Tezaurus snapshots and filter indexes."""

    def __init__(
        self,
        *,
        redis_client: Redis | None = None,
        prefix: str | None = None,
    ) -> None:
        self.redis = redis_client or Redis.from_url(settings.REDIS_CONN)
        configured_prefix = (prefix or settings.TEZAURUS_REDIS_PREFIX or "tezaurus:v1").strip(":")
        self.prefix = configured_prefix or "tezaurus:v1"

    @property
    def version_key(self) -> str:
        return f"{self.prefix}:version"

    @property
    def colors_key(self) -> str:
        return f"{self.prefix}:colors"

    @property
    def countries_key(self) -> str:
        return f"{self.prefix}:countries"

    @property
    def tnved_key(self) -> str:
        return f"{self.prefix}:tnved"

    @property
    def countries_index_key(self) -> str:
        return f"{self.prefix}:countries:index"

    def tnved_index_key(self, category: str | None) -> str:
        category_part = normalize_tnved_category(category)
        return f"{self.prefix}:tnved:index:category:{category_part}"

    def countries_filtered_key(self, *, category: str | None, our_rd: bool) -> str:
        our_rd_part = "1" if our_rd else "0"
        category_part = normalize_countries_category(category) if our_rd else "all"
        return f"{self.countries_key}:our_rd:{our_rd_part}:category:{category_part}"

    def tnved_filtered_key(
        self,
        *,
        category: str | None,
        subcategory: str | None = None,
        type_name: str | None = None,
        gender: str | None = None,
    ) -> str:
        key = f"{self.tnved_key}:category:{normalize_tnved_category(category)}"

        if subcategory is None:
            return key

        key = f"{key}:subcategory:{normalize_tnved_subcategory(subcategory)}"
        if type_name is None:
            return key

        key = f"{key}:type:{normalize_key_part(type_name)}"
        if gender is None:
            return key

        return f"{key}:gender:{normalize_tnved_gender(gender)}"

    def _serialize(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    def _set_json(self, key: str, payload: Any, pipe=None) -> None:
        encoded = self._serialize(payload)
        target = pipe or self.redis
        target.set(key, encoded)

    def _get_json(self, key: str, *, default: Any = None) -> Any:
        raw_value = self.redis.get(key)
        if raw_value is None:
            return default

        if isinstance(raw_value, bytes):
            raw_value = raw_value.decode("utf-8")

        try:
            return json.loads(raw_value)
        except (TypeError, ValueError):
            logger.exception("Failed to decode tezaurus JSON payload from Redis key {}", key)
            return default

    def _next_versions(
        self,
        *,
        current_versions: dict[str, Any],
        dictionary_name: str,
        remote_revision: dict[str, Any],
    ) -> dict[str, Any]:
        next_versions = dict(current_versions or {})
        next_versions[dictionary_name] = {
            "revision": _as_int(remote_revision.get("revision"), default=0),
            "updated_at": remote_revision.get("updated_at"),
        }
        next_versions["synced_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        return next_versions

    def save_dictionary_version(
        self,
        *,
        dictionary_name: str,
        remote_revision: dict[str, Any],
        current_versions: dict[str, Any],
    ) -> dict[str, Any]:
        next_versions = self._next_versions(
            current_versions=current_versions,
            dictionary_name=dictionary_name,
            remote_revision=remote_revision,
        )
        self._set_json(self.version_key, next_versions)
        return next_versions

    def get_versions(self) -> dict[str, Any]:
        versions = self._get_json(self.version_key, default={})
        return versions if isinstance(versions, dict) else {}

    def get_colors_snapshot(self) -> dict[str, Any]:
        payload = self._get_json(self.colors_key, default={})
        return payload if isinstance(payload, dict) else {}

    def get_countries_snapshot(self) -> dict[str, Any]:
        payload = self._get_json(self.countries_key, default={})
        return payload if isinstance(payload, dict) else {}

    def get_tnved_snapshot(self) -> dict[str, Any]:
        payload = self._get_json(self.tnved_key, default={})
        return payload if isinstance(payload, dict) else {}

    def has_colors_data(self) -> bool:
        return bool(self.redis.exists(self.colors_key))

    def has_countries_data(self) -> bool:
        return bool(self.redis.exists(self.countries_key))

    def has_tnved_category(self, category: str) -> bool:
        return bool(self.redis.exists(self.tnved_filtered_key(category=category)))

    def save_colors(
        self,
        *,
        payload: dict[str, Any],
        remote_revision: dict[str, Any],
        current_versions: dict[str, Any],
    ) -> dict[str, Any]:
        if payload.get("ok") is not True:
            raise TezaurusStorageError("Colors payload is not successful")

        items = payload.get("items")
        if not isinstance(items, list):
            raise TezaurusStorageError("Colors payload has invalid items format")

        snapshot = {
            "revision": _as_int(payload.get("revision"), default=_as_int(remote_revision.get("revision"), default=0)),
            "items": items,
        }

        next_versions = self._next_versions(
            current_versions=current_versions,
            dictionary_name=DICTIONARY_COLORS,
            remote_revision=remote_revision,
        )

        with self.redis.pipeline(transaction=True) as pipe:
            self._set_json(self.colors_key, snapshot, pipe=pipe)
            self._set_json(self.version_key, next_versions, pipe=pipe)
            pipe.execute()

        return next_versions

    def save_countries(
        self,
        *,
        payload: dict[str, Any],
        remote_revision: dict[str, Any],
        current_versions: dict[str, Any],
    ) -> dict[str, Any]:
        if payload.get("ok") is not True:
            raise TezaurusStorageError("Countries payload is not successful")

        raw_items = payload.get("items")
        if not isinstance(raw_items, dict):
            raise TezaurusStorageError("Countries payload has invalid items format")

        user_rd = raw_items.get("user_rd")
        if not isinstance(user_rd, list):
            raise TezaurusStorageError("Countries payload has invalid user_rd format")

        raw_our_rd = raw_items.get("our_rd")
        if not isinstance(raw_our_rd, dict):
            raise TezaurusStorageError("Countries payload has invalid our_rd format")

        our_rd: dict[str, list[Any]] = {}
        for category_name, category_values in raw_our_rd.items():
            if not isinstance(category_values, list):
                raise TezaurusStorageError("Countries payload has non-list category values")
            our_rd[str(category_name)] = category_values

        snapshot = {
            "revision": _as_int(payload.get("revision"), default=_as_int(remote_revision.get("revision"), default=0)),
            "items": {
                "user_rd": user_rd,
                "our_rd": our_rd,
            },
        }

        filtered_entries: dict[str, Any] = {
            self.countries_filtered_key(category=None, our_rd=False): user_rd,
            self.countries_filtered_key(category=None, our_rd=True): our_rd,
        }

        for category_name, category_values in our_rd.items():
            filtered_entries[self.countries_filtered_key(category=category_name, our_rd=True)] = category_values

        previous_index = self._get_json(self.countries_index_key, default=[])
        previous_keys = [value for value in previous_index if isinstance(value, str)] if isinstance(previous_index, list) else []

        next_versions = self._next_versions(
            current_versions=current_versions,
            dictionary_name=DICTIONARY_COUNTRIES,
            remote_revision=remote_revision,
        )

        with self.redis.pipeline(transaction=True) as pipe:
            if previous_keys:
                pipe.delete(*previous_keys)

            for key, value in filtered_entries.items():
                self._set_json(key, value, pipe=pipe)

            self._set_json(self.countries_index_key, list(filtered_entries.keys()), pipe=pipe)
            self._set_json(self.countries_key, snapshot, pipe=pipe)
            self._set_json(self.version_key, next_versions, pipe=pipe)
            pipe.execute()

        return next_versions

    def save_tnved_category(
        self,
        *,
        category_slug: str,
        payload: dict[str, Any],
    ) -> None:
        if payload.get("ok") is not True:
            raise TezaurusStorageError("TNVED payload is not successful")

        raw_items = payload.get("items")
        if not isinstance(raw_items, dict):
            raise TezaurusStorageError("TNVED payload has invalid items format")

        subcategories = raw_items.get("subcategories")
        if not isinstance(subcategories, dict):
            raise TezaurusStorageError("TNVED payload has invalid subcategories format")

        normalized_category = normalize_tnved_category(category_slug)
        category_snapshot = {
            "revision": _as_int(payload.get("revision"), default=0),
            "category": payload.get("category"),
            "items": {
                "subcategories": subcategories,
            },
        }

        filtered_entries = self._build_tnved_entries(
            category_slug=normalized_category,
            category_snapshot=category_snapshot,
        )

        tnved_snapshot = self.get_tnved_snapshot()
        tnved_snapshot[normalized_category] = category_snapshot

        previous_index = self._get_json(self.tnved_index_key(normalized_category), default=[])
        previous_keys = [value for value in previous_index if isinstance(value, str)] if isinstance(previous_index, list) else []

        with self.redis.pipeline(transaction=True) as pipe:
            if previous_keys:
                pipe.delete(*previous_keys)

            for key, value in filtered_entries.items():
                self._set_json(key, value, pipe=pipe)

            self._set_json(self.tnved_index_key(normalized_category), list(filtered_entries.keys()), pipe=pipe)
            self._set_json(self.tnved_key, tnved_snapshot, pipe=pipe)
            pipe.execute()

    def _build_tnved_entries(
        self,
        *,
        category_slug: str,
        category_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        entries: dict[str, Any] = {
            self.tnved_filtered_key(category=category_slug): category_snapshot,
        }

        subcategories = (category_snapshot.get("items") or {}).get("subcategories") or {}
        for subcategory_name, type_items in subcategories.items():
            subcategory_key = self.tnved_filtered_key(category=category_slug, subcategory=str(subcategory_name))
            entries[subcategory_key] = type_items if isinstance(type_items, list) else []

            if not isinstance(type_items, list):
                continue

            for type_item in type_items:
                if not isinstance(type_item, dict):
                    continue

                type_name = type_item.get("name")
                if not type_name:
                    continue

                type_key = self.tnved_filtered_key(
                    category=category_slug,
                    subcategory=str(subcategory_name),
                    type_name=str(type_name),
                )
                entries[type_key] = type_item

                genders = type_item.get("genders") or []
                if not isinstance(genders, list):
                    continue

                for gender_item in genders:
                    if not isinstance(gender_item, dict):
                        continue

                    gender_name = gender_item.get("name")
                    if not gender_name:
                        continue

                    gender_key = self.tnved_filtered_key(
                        category=category_slug,
                        subcategory=str(subcategory_name),
                        type_name=str(type_name),
                        gender=str(gender_name),
                    )

                    codes = gender_item.get("codes") or []
                    entries[gender_key] = codes if isinstance(codes, list) else []

        return entries

    def get_countries_by_filter(self, *, category: str | None, our_rd: bool) -> Any:
        return self._get_json(self.countries_filtered_key(category=category, our_rd=our_rd), default=None)

    def get_tnved_by_filter(
        self,
        *,
        category: str,
        subcategory: str | None = None,
        type_name: str | None = None,
        gender: str | None = None,
    ) -> Any:
        key = self.tnved_filtered_key(
            category=category,
            subcategory=subcategory,
            type_name=type_name,
            gender=gender,
        )
        return self._get_json(key, default=None)
