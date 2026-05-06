from __future__ import annotations

from functools import lru_cache

from config import settings
from logger import logger

from .cache_service import TezaurusCacheService


_RD_CATEGORY_MAP = {
    settings.Clothes.CATEGORY_PROCESS: "clothes",
    settings.Socks.CATEGORY_PROCESS: "clothes",
    settings.Shoes.CATEGORY_PROCESS: "shoes",
    settings.Linen.CATEGORY_PROCESS: "linen",
    settings.Parfum.CATEGORY_PROCESS: "parfum",
}

_RD_FALLBACKS = {
    "clothes": settings.CLOTHES_COUNTRIES_RD,
    "shoes": settings.SHOES_COUNTRIES_RD,
    "linen": settings.LINEN_COUNTRIES_RD,
    "parfum": settings.PARFUM_COUNTRIES_RD,
}


def _normalize_str_list(values) -> list[str]:
    if not isinstance(values, list):
        return []

    normalized: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        normalized.append(text.upper())
    return normalized


@lru_cache(maxsize=1)
def _get_cache_service() -> TezaurusCacheService:
    return TezaurusCacheService()


def get_colors() -> list[str]:
    try:
        colors = _normalize_str_list(_get_cache_service().get_all_colors())
        if colors:
            return colors
    except Exception:
        logger.exception("Failed to read colors from Tezaurus Redis cache")

    return _normalize_str_list(list(settings.ALL_COLORS))


def get_all_countries() -> list[str]:
    try:
        countries = _normalize_str_list(_get_cache_service().get_countries(our_rd=False))
        if countries:
            return countries
    except Exception:
        logger.exception("Failed to read countries from Tezaurus Redis cache")

    return _normalize_str_list(list(settings.COUNTRIES_LIST))


def get_rd_countries(category: str) -> list[str]:
    normalized_category = _RD_CATEGORY_MAP.get(category, category)
    try:
        countries = _normalize_str_list(
            _get_cache_service().get_countries(category=normalized_category, our_rd=True)
        )
        if countries:
            return countries
    except Exception:
        logger.exception("Failed to read RD countries from Tezaurus Redis cache for category %s", normalized_category)

    fallback = _RD_FALLBACKS.get(normalized_category, settings.COUNTRIES_LIST)
    return _normalize_str_list(list(fallback))


def is_allowed_color(color: str) -> bool:
    return (color or "").strip().upper() in set(get_colors())


def is_allowed_country(country: str) -> bool:
    return (country or "").strip().upper() in set(get_all_countries())
