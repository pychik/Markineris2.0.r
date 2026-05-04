from __future__ import annotations

import re
import unicodedata


TNVED_CATEGORY_ALIASES = {
    "clothes": "clothes",
    "odezhda": "clothes",
    "одежда": "clothes",
}

TNVED_SUBCATEGORY_ALIASES = {
    "common": "common",
    "obshchee": "common",
    "общее": "common",
    "underwear": "underwear",
    "nizhnee_bele": "underwear",
    "нижнее_белье": "underwear",
}

COUNTRIES_CATEGORY_ALIASES = {
    "clothes": "clothes",
    "одежда": "clothes",
    "shoes": "shoes",
    "обувь": "shoes",
    "linen": "linen",
    "белье": "linen",
    "parfum": "parfum",
    "парфюм": "parfum",
    "парфюмерия": "parfum",
}

TNVED_GENDER_ALIASES = {
    "без_указания_пола": "no_gender",
    "безпола": "no_gender",
    "унисекс": "no_gender",
    "unisex": "no_gender",
    "жен": "female",
    "женский": "female",
    "женская": "female",
    "female": "female",
    "муж": "male",
    "мужской": "male",
    "мужская": "male",
    "male": "male",
}


def normalize_key_part(value: object | None) -> str:
    if value is None:
        return "all"

    if isinstance(value, bool):
        return "1" if value else "0"

    text = str(value).strip().lower()
    if not text:
        return "all"

    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", "_", text)
    text = text.replace("/", "_")
    text = re.sub(r"[^\w\-]", "", text, flags=re.UNICODE)
    text = text.strip("_")
    return text or "all"


def normalize_tnved_category(value: object | None) -> str:
    normalized = normalize_key_part(value)
    return TNVED_CATEGORY_ALIASES.get(normalized, normalized)


def normalize_tnved_subcategory(value: object | None) -> str:
    normalized = normalize_key_part(value)
    return TNVED_SUBCATEGORY_ALIASES.get(normalized, normalized)


def normalize_countries_category(value: object | None) -> str:
    normalized = normalize_key_part(value)
    return COUNTRIES_CATEGORY_ALIASES.get(normalized, normalized)


def normalize_tnved_gender(value: object | None) -> str:
    normalized = normalize_key_part(value)
    return TNVED_GENDER_ALIASES.get(normalized, normalized)
