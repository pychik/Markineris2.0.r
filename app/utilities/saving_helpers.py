"""Helpers for merging duplicate order positions during save flows."""

from __future__ import annotations

import re
from typing import Any

from config import settings
from utilities.exceptions import SizeTypeException

NO_TRADEMARK_VALUE = 'без товарного знака'
NO_ARTICLE_VALUE = 'отсутствует'
NO_TRADEMARK_PLACEHOLDERS = {'БЕЗ ТОВАРНОГО ЗНАКА'}
NO_ARTICLE_PLACEHOLDERS = {'БЕЗ АРТИКУЛА', 'ОТСУТСТВУЕТ'}
LEGACY_LENGTH_WIDTH_SIZE_TYPE = 'ДЛИНА*ШИРИНА'


def process_input_str(value: str | None) -> str:
    """Normalize free-form text fields before they are stored or compared."""
    if value is None:
        return ""
    return value.replace("\"", '').replace("\'", '').replace(":", '').replace("?", '').strip()


def normalize_trademark_placeholder(value: str) -> str:
    """Replace placeholder-only trademark values with the canonical fallback."""
    cleaned = process_input_str(value or "")
    if not cleaned:
        return cleaned

    compact = cleaned.replace(' ', '')
    if compact and len(set(compact)) == 1 and not compact[0].isalnum():
        return NO_TRADEMARK_VALUE

    return cleaned


def normalize_placeholder_value(value: Any, placeholders: set[str], replacement: str) -> Any:
    normalized = normalize_key_value(value)
    if isinstance(normalized, str) and normalized.upper() in placeholders:
        return replacement
    return normalized


def normalize_article_placeholder(value: str | None) -> str:
    return normalize_placeholder_value(process_input_str(value), NO_ARTICLE_PLACEHOLDERS, NO_ARTICLE_VALUE)


def is_length_width_size_type(size_type: str | None) -> bool:
    return str(size_type or '').strip() in {settings.Clothes.LENGTH_WIDTH_SIZE_TYPE, LEGACY_LENGTH_WIDTH_SIZE_TYPE}


def normalize_length_width_size_type(size_type: str | None) -> str:
    normalized_type = str(size_type or '').strip()
    if is_length_width_size_type(normalized_type):
        return settings.Clothes.LENGTH_WIDTH_SIZE_TYPE
    return normalized_type


def normalize_length_width_size_value(size: str | None, size_type: str | None) -> str:
    normalized_size = str(size or '').strip()
    if not is_length_width_size_type(size_type):
        return normalized_size

    return (
        normalized_size
        .replace('*', '-')
        .replace('x', '-')
        .replace('X', '-')
        .replace('х', '-')
        .replace('Х', '-')
    )


def normalize_key_value(value: Any) -> Any:
    """Trim string values before they participate in merge keys."""
    if isinstance(value, str):
        return value.strip()
    return value


def normalize_int_key(value: Any) -> int:
    """Convert nullable numeric-like values to an integer key component."""
    if value in (None, ''):
        return 0
    return int(value)


def normalize_float_key(value: Any) -> float:
    """Convert nullable numeric-like values to a float key component."""
    if value in (None, ''):
        return 0.0
    return float(value)


def get_clothes_size_type(size: str, provided_type: str) -> str:
    """Validate a clothes size value and map it to the normalized size type."""
    if not provided_type:
        raise SizeTypeException("Тип размера не указан.")

    provided_type = provided_type.strip()
    length_width_size_type = settings.Clothes.LENGTH_WIDTH_SIZE_TYPE

    if is_length_width_size_type(provided_type):
        normalized_size = (size or '').strip()
        size_match = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*[-*xх]\s*(\d+(?:[.,]\d+)?)\s+(мм|см)', normalized_size)
        if not size_match:
            raise SizeTypeException(
                f"Размер '{size}' не соответствует типу '{length_width_size_type}'."
            )
        length_value, width_value, unit_value = size_match.groups()
        if unit_value not in {'мм', 'см'}:
            raise SizeTypeException(
                f"Размер '{size}' не соответствует типу '{length_width_size_type}'."
            )
        if float(length_value.replace(',', '.')) <= 0 or float(width_value.replace(',', '.')) <= 0:
            raise SizeTypeException(
                f"Размер '{size}' не соответствует типу '{length_width_size_type}'."
            )
        return length_width_size_type

    valid_keys = settings.Clothes.SIZE_ALL_DICT.keys()
    if provided_type not in valid_keys:
        raise SizeTypeException(f"Неизвестный тип размера: '{provided_type}'.")

    if provided_type == 'РОССИЯ':
        valid_sizes = settings.Clothes.CLOTHES_ST_RUSSIA
        if size not in valid_sizes:
            raise SizeTypeException(
                f"Размер '{size}' не соответствует типу 'РОССИЯ'."
            )
        return settings.Clothes.DEFAULT_SIZE_TYPE

    if provided_type == 'МЕЖДУНАРОДНЫЙ':
        return settings.Clothes.INTERNATIONAL_SIZE_TYPE

    if provided_type == 'ОСОБЫЕ_РАЗМЕРЫ':
        return settings.Clothes.INTERNATIONAL_SIZE_TYPE

    if provided_type == 'РОСТ':
        return settings.Clothes.ROST_SIZE_TYPE

    raise SizeTypeException(f"Не удалось определить size_type для '{provided_type}'.")


def build_position_key(item: Any, category: str) -> tuple:
    """Build a stable comparison key for an order position."""
    common = (
        normalize_placeholder_value(item.trademark, NO_TRADEMARK_PLACEHOLDERS, NO_TRADEMARK_VALUE),
        normalize_key_value(item.tnved_code),
        normalize_key_value(item.country),
        normalize_key_value(item.rd_type),
        normalize_key_value(item.rd_name),
        item.rd_date,
        normalize_float_key(item.article_price),
        normalize_int_key(item.tax),
        normalize_key_value(item.type),
    )

    match category:
        case settings.Shoes.CATEGORY:
            return common + (
                normalize_placeholder_value(item.article, NO_ARTICLE_PLACEHOLDERS, NO_ARTICLE_VALUE),
                normalize_key_value(item.color),
                normalize_key_value(item.material_top),
                normalize_key_value(item.material_lining),
                normalize_key_value(item.material_bottom),
                normalize_key_value(item.gender),
            )
        case settings.Clothes.CATEGORY:
            return common + (
                normalize_placeholder_value(item.article, NO_ARTICLE_PLACEHOLDERS, NO_ARTICLE_VALUE),
                normalize_key_value(item.color),
                normalize_key_value(item.gender),
                normalize_key_value(item.content),
                normalize_key_value(item.subcategory),
            )
        case settings.Socks.CATEGORY:
            return common + (
                normalize_placeholder_value(item.article, NO_ARTICLE_PLACEHOLDERS, NO_ARTICLE_VALUE),
                normalize_key_value(item.color),
                normalize_key_value(item.gender),
                normalize_key_value(item.content),
            )
        case settings.Linen.CATEGORY:
            return common + (
                normalize_placeholder_value(item.article, NO_ARTICLE_PLACEHOLDERS, NO_ARTICLE_VALUE),
                normalize_key_value(item.color),
                normalize_key_value(item.customer_age),
                normalize_key_value(item.textile_type),
                normalize_key_value(item.content),
            )
        case settings.Parfum.CATEGORY:
            return common + (
                normalize_key_value(item.volume_type),
                normalize_key_value(item.volume),
                normalize_key_value(item.package_type),
                normalize_key_value(item.material_package),
            )
        case settings.Cosmetics.CATEGORY:
            return common + (
                normalize_key_value(item.full_name_extra),
                normalize_key_value(item.subcategory),
                normalize_key_value(item.nominal_quantity_type),
                normalize_int_key(item.nominal_quantity),
                normalize_int_key(getattr(item, "blade_count", None)),
                normalize_key_value(getattr(item, "complectation", None)),
                normalize_key_value(getattr(item, "layers_characteristic", None)),
                bool(item.for_children),
                normalize_key_value(item.usage_term_type),
                normalize_key_value(item.content_type),
                normalize_key_value(item.content),
                normalize_int_key(item.service_life),
                item.sl_date_from,
                item.sl_date_to,
            )
    raise ValueError(f"Unsupported category for merge: {category}")


def build_size_key(size_obj: Any, category: str) -> tuple:
    """Build a stable comparison key for a size row inside one position."""
    match category:
        case settings.Shoes.CATEGORY:
            return (normalize_key_value(size_obj.size),)
        case settings.Clothes.CATEGORY | settings.Socks.CATEGORY:
            return (
                normalize_length_width_size_value(size_obj.size, size_obj.size_type),
                normalize_length_width_size_type(size_obj.size_type),
            )
        case settings.Linen.CATEGORY:
            return (normalize_key_value(size_obj.size), normalize_key_value(getattr(size_obj, "unit", None)))
    raise ValueError(f"Unsupported category for size merge: {category}")


def merge_size_quantities(existing_item: Any, new_item: Any, category: str, old_sq_map: dict | None = None,
                          source_size_pairs: list[tuple[int, object]] | None = None) -> None:
    """Merge size quantities from a new position into an existing one."""
    existing_by_key = {build_size_key(size_obj, category): size_obj for size_obj in existing_item.sizes_quantities}
    source_old_ids = {id(size_obj): old_id for old_id, size_obj in (source_size_pairs or [])}

    for new_size_obj in new_item.sizes_quantities:
        key = build_size_key(new_size_obj, category)
        existing_size_obj = existing_by_key.get(key)
        target_size_obj = new_size_obj
        if existing_size_obj is None:
            existing_item.sizes_quantities.append(new_size_obj)
            existing_by_key[key] = new_size_obj
        else:
            existing_size_obj.quantity = normalize_int_key(existing_size_obj.quantity) + normalize_int_key(new_size_obj.quantity)
            target_size_obj = existing_size_obj

        if old_sq_map is not None:
            old_sq_id = source_old_ids.get(id(new_size_obj))
            if old_sq_id is not None:
                old_sq_map[old_sq_id] = target_size_obj


def append_or_merge_position(order_positions: Any, new_item: Any, category: str, old_sq_map: dict | None = None,
                             source_size_pairs: list[tuple[int, object]] | None = None):
    """Append a new position or merge it into an existing matching one."""
    new_key = build_position_key(new_item, category)
    # logger.info(f"merge check category={category} new_key={new_key}")
    for existing_item in order_positions:
        existing_key = build_position_key(existing_item, category)
        # logger.info(f"merge compare category={category} existing_key={existing_key}")
        if existing_key != new_key:
            continue

        if category == settings.Parfum.CATEGORY:
            existing_item.quantity = normalize_int_key(existing_item.quantity) + normalize_int_key(new_item.quantity)
            return existing_item

        if category == settings.Cosmetics.CATEGORY:
            existing_item.quantity = normalize_int_key(existing_item.quantity) + normalize_int_key(new_item.quantity)
            return existing_item

        merge_size_quantities(existing_item, new_item, category, old_sq_map=old_sq_map,
                              source_size_pairs=source_size_pairs)
        return existing_item

    order_positions.append(new_item)
    if old_sq_map is not None:
        for old_sq_id, size_obj in (source_size_pairs or []):
            old_sq_map[old_sq_id] = size_obj
    return new_item
