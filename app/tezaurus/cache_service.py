from __future__ import annotations

from typing import Any

from config import settings
from tezaurus_fallback.repository import LocalTezaurusRepository

from .constants import DEFAULT_TNVED_CATEGORY_SLUG
from .redis_repository import RedisTezaurusRepository


class TezaurusCacheService:
    """Read-only API for the configured Tezaurus catalog source."""

    def __init__(self, *, repository: RedisTezaurusRepository | LocalTezaurusRepository | None = None) -> None:
        self.repository = repository if repository is not None else (
            RedisTezaurusRepository() if settings.TEZAURUS_SYNC_ENABLED else LocalTezaurusRepository()
        )

    def get_versions(self) -> dict[str, Any]:
        return self.repository.get_versions()

    def get_all_colors(self) -> list[Any]:
        colors_snapshot = self.repository.get_colors_snapshot()
        items = colors_snapshot.get("items") if isinstance(colors_snapshot, dict) else []
        return items if isinstance(items, list) else []

    def get_processing_companies(self) -> list[Any]:
        companies = self.repository.get_processing_companies()
        return companies if isinstance(companies, list) else []

    def get_countries(self, *, category: str | None = None, our_rd: bool = False) -> Any:
        value = self.repository.get_countries_by_filter(category=category, our_rd=our_rd)
        if value is not None:
            return value

        if our_rd and category is None:
            return {}

        return []

    def get_tnved(
        self,
        *,
        category: str = DEFAULT_TNVED_CATEGORY_SLUG,
        subcategory: str | None = None,
        type_name: str | None = None,
        gender: str | None = None,
    ) -> Any:
        value = self.repository.get_tnved_by_filter(
            category=category,
            subcategory=subcategory,
            type_name=type_name,
            gender=gender,
        )
        if value is not None:
            return value

        if gender is not None:
            return []
        if type_name is not None:
            return {}
        if subcategory is not None:
            return []
        return {}
