from __future__ import annotations

import uuid
from typing import Any

import redis
from redis import Redis

from logger import logger

from .api_client import TezaurusApiClient
from .constants import (
    DEFAULT_TNVED_CATEGORY_SLUG,
    DICTIONARIES,
    DICTIONARY_COLORS,
    DICTIONARY_COUNTRIES,
    DICTIONARY_TNVED,
)
from .redis_repository import RedisTezaurusRepository


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class TezaurusSyncService:
    """Service that syncs remote Tezaurus dictionaries into Redis."""

    _LOCK_RELEASE_SCRIPT = (
        'if redis.call("GET", KEYS[1]) == ARGV[1] then '
        'return redis.call("DEL", KEYS[1]) '
        'else return 0 end'
    )

    def __init__(
        self,
        *,
        api_client: TezaurusApiClient,
        repository: RedisTezaurusRepository,
        tnved_categories: tuple[str, ...] | None = None,
        lock_key: str | None = None,
        lock_ttl_seconds: int = 300,
    ) -> None:
        self.api_client = api_client
        self.repository = repository
        self.tnved_categories = tnved_categories or (DEFAULT_TNVED_CATEGORY_SLUG,)
        self.lock_key = lock_key or f"{self.repository.prefix}:sync:lock"
        self.lock_ttl_seconds = max(int(lock_ttl_seconds), 1)

    def sync(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "ok": True,
            "updated": [],
            "skipped": [],
            "failed": [],
        }

        lock_token = uuid.uuid4().hex
        try:
            lock_acquired = self._acquire_lock(lock_token)
        except redis.RedisError:
            logger.exception("Failed to acquire Tezaurus sync lock")
            result["ok"] = False
            result["failed"].append("lock")
            result["reason"] = "lock_error"
            return result

        if not lock_acquired:
            result["skipped"].append("sync_lock")
            result["reason"] = "sync_lock_busy"
            return result

        try:
            try:
                state_payload = self.api_client.get_dictionaries_state()
                remote_revisions = self._extract_revisions(state_payload)
            except Exception:
                logger.exception("Failed to fetch or parse dictionaries revisions from Tezaurus")
                result["ok"] = False
                result["failed"].append("revisions")
                return result

            versions = self.repository.get_versions()

            versions = self._sync_colors(versions=versions, remote_revisions=remote_revisions, result=result)
            versions = self._sync_countries(versions=versions, remote_revisions=remote_revisions, result=result)
            versions = self._sync_tnved(versions=versions, remote_revisions=remote_revisions, result=result)

            result["ok"] = not result["failed"]
            result["versions"] = versions
            return result
        finally:
            self._release_lock(lock_token)

    def _sync_colors(
        self,
        *,
        versions: dict[str, Any],
        remote_revisions: dict[str, dict[str, Any]],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._needs_update(
            dictionary_name=DICTIONARY_COLORS,
            remote_revisions=remote_revisions,
            current_versions=versions,
            has_data=self.repository.has_colors_data(),
        ):
            result["skipped"].append(DICTIONARY_COLORS)
            return versions

        try:
            payload = self.api_client.export_colors()
            versions = self.repository.save_colors(
                payload=payload,
                remote_revision=remote_revisions[DICTIONARY_COLORS],
                current_versions=versions,
            )
            result["updated"].append(DICTIONARY_COLORS)
            return versions
        except Exception:
            logger.exception("Failed to sync colors dictionary")
            result["failed"].append(DICTIONARY_COLORS)
            return versions

    def _sync_countries(
        self,
        *,
        versions: dict[str, Any],
        remote_revisions: dict[str, dict[str, Any]],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._needs_update(
            dictionary_name=DICTIONARY_COUNTRIES,
            remote_revisions=remote_revisions,
            current_versions=versions,
            has_data=self.repository.has_countries_data(),
        ):
            result["skipped"].append(DICTIONARY_COUNTRIES)
            return versions

        try:
            payload = self.api_client.export_countries()
            versions = self.repository.save_countries(
                payload=payload,
                remote_revision=remote_revisions[DICTIONARY_COUNTRIES],
                current_versions=versions,
            )
            result["updated"].append(DICTIONARY_COUNTRIES)
            return versions
        except Exception:
            logger.exception("Failed to sync countries dictionary")
            result["failed"].append(DICTIONARY_COUNTRIES)
            return versions

    def _sync_tnved(
        self,
        *,
        versions: dict[str, Any],
        remote_revisions: dict[str, dict[str, Any]],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        revision_changed = self._needs_update(
            dictionary_name=DICTIONARY_TNVED,
            remote_revisions=remote_revisions,
            current_versions=versions,
            has_data=all(self.repository.has_tnved_category(category) for category in self.tnved_categories),
        )

        categories_to_sync = [
            category
            for category in self.tnved_categories
            if revision_changed or not self.repository.has_tnved_category(category)
        ]

        if not categories_to_sync:
            result["skipped"].append(DICTIONARY_TNVED)
            return versions

        updated_any = False
        failed_any = False
        for category in categories_to_sync:
            try:
                payload = self.api_client.export_tnved(category)
                self.repository.save_tnved_category(
                    category_slug=category,
                    payload=payload,
                )
                updated_any = True
            except Exception:
                logger.exception("Failed to sync tnved dictionary for category {}", category)
                result["failed"].append(f"{DICTIONARY_TNVED}:{category}")
                failed_any = True

        if failed_any:
            return versions

        if updated_any:
            versions = self.repository.save_dictionary_version(
                dictionary_name=DICTIONARY_TNVED,
                remote_revision=remote_revisions[DICTIONARY_TNVED],
                current_versions=versions,
            )
            result["updated"].append(DICTIONARY_TNVED)
        else:
            result["skipped"].append(DICTIONARY_TNVED)

        return versions

    def _needs_update(
        self,
        *,
        dictionary_name: str,
        remote_revisions: dict[str, dict[str, Any]],
        current_versions: dict[str, Any],
        has_data: bool,
    ) -> bool:
        remote_revision = _as_int((remote_revisions.get(dictionary_name) or {}).get("revision"), default=0)
        local_revision = self._local_revision(current_versions, dictionary_name)
        return remote_revision != local_revision or not has_data

    def _local_revision(self, versions: dict[str, Any], dictionary_name: str) -> int:
        value = (versions.get(dictionary_name) or {}).get("revision")
        return _as_int(value, default=-1)

    def _extract_revisions(self, payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        if payload.get("ok") is not True:
            raise ValueError("Dictionaries-state response is not successful")

        revisions_payload = payload.get("revisions")
        if not isinstance(revisions_payload, dict):
            raise ValueError("Missing revisions section in dictionaries-state response")

        parsed: dict[str, dict[str, Any]] = {}
        for dictionary_name in DICTIONARIES:
            raw_entry = revisions_payload.get(dictionary_name)
            if not isinstance(raw_entry, dict):
                raise ValueError(f"Missing revision entry for {dictionary_name}")

            parsed[dictionary_name] = {
                "revision": _as_int(raw_entry.get("revision"), default=0),
                "updated_at": raw_entry.get("updated_at"),
            }

        return parsed

    def _acquire_lock(self, token: str) -> bool:
        return bool(
            self.repository.redis.set(
                self.lock_key,
                token,
                nx=True,
                ex=self.lock_ttl_seconds,
            )
        )

    def _release_lock(self, token: str) -> None:
        try:
            self.repository.redis.eval(self._LOCK_RELEASE_SCRIPT, 1, self.lock_key, token)
        except redis.RedisError:
            logger.warning("Failed to release Tezaurus sync lock key {}", self.lock_key)


def build_default_tezaurus_sync_service(*, redis_client: Redis | None = None) -> TezaurusSyncService:
    repository = RedisTezaurusRepository(redis_client=redis_client)
    api_client = TezaurusApiClient()
    return TezaurusSyncService(api_client=api_client, repository=repository)
