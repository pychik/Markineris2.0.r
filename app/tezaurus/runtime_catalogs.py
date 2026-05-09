from __future__ import annotations

from functools import lru_cache

from config import settings
from logger import logger

from .cache_service import TezaurusCacheService
from .key_builder import normalize_tnved_subcategory

from utilities.categories_data.clothes_common.clothes_common_tnved_by_gender import CLOTHES_GENDERS_ORDER_RAW
from utilities.categories_data.clothes_common.tnved_processor import get_tnved_gender_clothes_common
from utilities.categories_data.clothes_common.types_genders import CLOTHES_TYPE_GENDERS
from utilities.categories_data.subcategories_data import ClothesSubcategories
from utilities.categories_data.underwear_data import (
    UNDERWEAR_TNVED_DICT,
    UNDERWEAR_TNVEDS,
    UNDERWEAR_TYPE_GENDERS,
    UNDERWEAR_TYPES,
    UNDERWEAR_TYPES_CARDS,
)


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

_DISPLAY_TO_REDIS_GENDER = {
    "Жен.": "Женский",
    "Женский": "Женский",
    "Муж.": "Мужской",
    "Мужской": "Мужской",
    "Унисекс": "Унисекс",
    "Без указания пола": "Без указания пола",
    "Детск.": "Без указания пола",
}

_REDIS_TO_DISPLAY_GENDER = {
    "ЖЕНСКИЙ": "Жен.",
    "МУЖСКОЙ": "Муж.",
    "УНИСЕКС": "Унисекс",
    "БЕЗ УКАЗАНИЯ ПОЛА": "Без указания пола",
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


def _normalize_subcategory(subcategory: str | None) -> str:
    if subcategory in ("", None, "None"):
        return ClothesSubcategories.common.value
    return normalize_tnved_subcategory(subcategory)


def _normalize_gender_display(gender: str | None) -> str:
    if gender is None:
        return ""
    value = str(gender).strip()
    if not value:
        return ""
    return _DISPLAY_TO_REDIS_GENDER.get(value, value)


def _display_gender(gender_name: str | None) -> str:
    value = str(gender_name or "").strip().upper()
    if not value:
        return ""
    return _REDIS_TO_DISPLAY_GENDER.get(value, str(gender_name).strip())


def _gender_sort_key(gender_name: str) -> int:
    display_name = _display_gender(gender_name)
    try:
        return ["Без указания пола", "Жен.", "Муж.", "Унисекс"].index(display_name)
    except ValueError:
        return len(CLOTHES_GENDERS_ORDER_RAW) + 1


def _is_supported_clothes_subcategory(subcategory: str | None) -> bool:
    return _normalize_subcategory(subcategory) in {
        ClothesSubcategories.common.value,
        ClothesSubcategories.underwear.value,
    }


def _extract_tnved_type_payload(subcategory: str | None, type_name: str | None) -> dict:
    if not type_name or not _is_supported_clothes_subcategory(subcategory):
        return {}

    normalized_subcategory = _normalize_subcategory(subcategory)
    value = _get_cache_service().get_tnved(
        category="clothes",
        subcategory=normalized_subcategory,
        type_name=type_name,
    )
    return value if isinstance(value, dict) else {}


def _extract_gender_codes(gender_payload: dict) -> list[tuple[str, str]]:
    codes = gender_payload.get("codes") or []
    if not isinstance(codes, list):
        return []

    result: list[tuple[str, str]] = []
    for entry in codes:
        if not isinstance(entry, dict):
            continue
        code = str(entry.get("code") or "").strip()
        description = str(entry.get("description") or "").strip()
        if not code:
            continue
        result.append((code, description))
    return result


def _fallback_clothes_types(subcategory: str, *, is_cards: bool = False) -> list[str]:
    if subcategory == ClothesSubcategories.underwear.value:
        return list(UNDERWEAR_TYPES_CARDS if is_cards else UNDERWEAR_TYPES)
    return list(settings.Clothes.TYPES)


def _fallback_clothes_genders(subcategory: str, type_name: str) -> list[str]:
    if subcategory == ClothesSubcategories.underwear.value:
        return list(UNDERWEAR_TYPE_GENDERS.get(type_name) or [])
    return list(CLOTHES_TYPE_GENDERS.get(type_name) or [])


def _fallback_clothes_codes(subcategory: str, type_name: str, gender: str) -> list[tuple[str, str]]:
    if subcategory == ClothesSubcategories.underwear.value:
        return list(
            get_tnved_gender_clothes_common(
                type_name=type_name,
                gender=gender,
                data=UNDERWEAR_TNVED_DICT,
            )
            or ()
        )
    return list(get_tnved_gender_clothes_common(type_name=type_name, gender=gender) or ())


def _fallback_clothes_all_tnved(subcategory: str) -> list[str]:
    if subcategory == ClothesSubcategories.underwear.value:
        return list(UNDERWEAR_TNVEDS)
    return list(settings.Clothes.TNVED_ALL)


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


def get_clothes_tnved_types(subcategory: str | None, *, is_cards: bool = False) -> list[str]:
    normalized_subcategory = _normalize_subcategory(subcategory)
    if not _is_supported_clothes_subcategory(normalized_subcategory):
        return []

    try:
        type_items = _get_cache_service().get_tnved(category="clothes", subcategory=normalized_subcategory)
        if isinstance(type_items, list):
            types: list[str] = []
            for item in type_items:
                if not isinstance(item, dict):
                    continue
                type_name = str(item.get("name") or "").strip()
                if not type_name:
                    continue
                types.append(type_name)
            if types:
                return types
    except Exception:
        logger.exception("Failed to read clothes types from Tezaurus Redis cache for subcategory %s", normalized_subcategory)

    return _fallback_clothes_types(normalized_subcategory, is_cards=is_cards)


def get_clothes_tnved_genders(subcategory: str | None, type_name: str) -> list[str]:
    normalized_subcategory = _normalize_subcategory(subcategory)
    if not type_name or not _is_supported_clothes_subcategory(normalized_subcategory):
        return []

    try:
        type_payload = _extract_tnved_type_payload(normalized_subcategory, type_name)
        raw_genders = type_payload.get("genders") or []
        if isinstance(raw_genders, list):
            genders: list[str] = []
            for item in raw_genders:
                if not isinstance(item, dict):
                    continue
                display_name = _display_gender(item.get("name"))
                if display_name:
                    genders.append(display_name)
            if genders:
                return sorted(dict.fromkeys(genders), key=_gender_sort_key)
    except Exception:
        logger.exception(
            "Failed to read clothes genders from Tezaurus Redis cache for subcategory %s and type %s",
            normalized_subcategory,
            type_name,
        )

    return _fallback_clothes_genders(normalized_subcategory, type_name)


def get_clothes_tnved_pairs(subcategory: str | None, type_name: str, gender: str) -> list[tuple[str, str]]:
    normalized_subcategory = _normalize_subcategory(subcategory)
    normalized_gender = _normalize_gender_display(gender)
    if not type_name or not normalized_gender or not _is_supported_clothes_subcategory(normalized_subcategory):
        return []

    try:
        type_payload = _extract_tnved_type_payload(normalized_subcategory, type_name)
        raw_genders = type_payload.get("genders") or []
        if isinstance(raw_genders, list):
            for item in raw_genders:
                if not isinstance(item, dict):
                    continue
                current_gender = _normalize_gender_display(item.get("name"))
                if current_gender != normalized_gender:
                    continue
                pairs = _extract_gender_codes(item)
                if pairs:
                    return pairs
    except Exception:
        logger.exception(
            "Failed to read clothes tnved codes from Tezaurus Redis cache for subcategory %s, type %s, gender %s",
            normalized_subcategory,
            type_name,
            normalized_gender,
        )

    return _fallback_clothes_codes(normalized_subcategory, type_name, gender)


def get_clothes_tnved_codes(subcategory: str | None, type_name: str, gender: str) -> list[str]:
    return [code for code, _ in get_clothes_tnved_pairs(subcategory, type_name, gender)]


def get_clothes_all_tnved(subcategory: str | None) -> list[str]:
    normalized_subcategory = _normalize_subcategory(subcategory)
    if not _is_supported_clothes_subcategory(normalized_subcategory):
        return []

    try:
        type_items = _get_cache_service().get_tnved(category="clothes", subcategory=normalized_subcategory)
        if isinstance(type_items, list):
            codes: list[str] = []
            seen: set[str] = set()
            for type_item in type_items:
                if not isinstance(type_item, dict):
                    continue
                for gender_item in type_item.get("genders") or []:
                    if not isinstance(gender_item, dict):
                        continue
                    for code, _description in _extract_gender_codes(gender_item):
                        if code in seen:
                            continue
                        seen.add(code)
                        codes.append(code)
            if codes:
                return codes
    except Exception:
        logger.exception("Failed to read clothes all tnved from Tezaurus Redis cache for subcategory %s", normalized_subcategory)

    return _fallback_clothes_all_tnved(normalized_subcategory)
