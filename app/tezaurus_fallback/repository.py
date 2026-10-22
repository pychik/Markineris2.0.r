"""Read the checked-in Tezaurus snapshot with the Redis repository's API."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import settings

_SEED_DATA_DIR = Path(__file__).resolve().parent / "data"
_REQUIRED_FILES = (
    "versions.json",
    "colors.json",
    "countries.json",
    "clothes_tnved.json",
    "processing_companies.json",
)


def _is_valid_data_dir(data_dir: Path) -> bool:
    try:
        for filename in _REQUIRED_FILES:
            with (data_dir / filename).open(encoding="utf-8") as source:
                json.load(source)
    except (OSError, ValueError, TypeError):
        return False
    return True


@lru_cache(maxsize=1)
def _data_dir() -> Path:
    runtime_dir = Path(settings.TEZAURUS_FALLBACK_RUNTIME_DATA_DIR)
    if _is_valid_data_dir(runtime_dir):
        return runtime_dir
    return _SEED_DATA_DIR


@lru_cache(maxsize=None)
def _load(filename: str) -> Any:
    with (_data_dir() / filename).open(encoding="utf-8") as source:
        return json.load(source)


class LocalTezaurusRepository:
    def get_versions(self) -> dict[str, Any]:
        return _load("versions.json")

    def get_colors_snapshot(self) -> dict[str, Any]:
        return _load("colors.json")

    def get_countries_snapshot(self) -> dict[str, Any]:
        return _load("countries.json")

    def get_processing_companies(self) -> list[dict[str, Any]]:
        return _load("processing_companies.json")

    def get_rd_snapshot(self) -> dict[str, Any]:
        # rd.json необязателен: в снимках, выгруженных до РД, и в seed-файлах его нет
        try:
            snapshot = _load("rd.json")
        except (OSError, ValueError):
            return {}
        return snapshot if isinstance(snapshot, dict) else {}

    def get_countries_by_filter(self, *, category: str | None, our_rd: bool) -> Any:
        items = self.get_countries_snapshot()["items"]
        if not our_rd:
            return items["user_rd"]
        categories = items["our_rd"]
        if category is None:
            return categories

        from tezaurus.key_builder import normalize_countries_category

        return categories.get(normalize_countries_category(category))

    def get_tnved_by_filter(
        self,
        *,
        category: str,
        subcategory: str | None = None,
        type_name: str | None = None,
        gender: str | None = None,
    ) -> Any:
        from tezaurus.key_builder import (
            normalize_key_part,
            normalize_tnved_category,
            normalize_tnved_gender,
            normalize_tnved_subcategory,
        )

        if normalize_tnved_category(category) != "clothes":
            return None

        snapshot = _load("clothes_tnved.json")
        if subcategory is None:
            return snapshot

        types = snapshot["items"]["subcategories"].get(normalize_tnved_subcategory(subcategory))
        if type_name is None or types is None:
            return types

        normalized_type = normalize_key_part(type_name)
        type_item = next(
            (item for item in types if normalize_key_part(item.get("name")) == normalized_type),
            None,
        )
        if gender is None or type_item is None:
            return type_item

        genders = type_item.get("genders", [])
        gender_item = next((item for item in genders if item.get("name") == gender), None)
        if gender_item is None:
            normalized_gender = normalize_tnved_gender(gender)
            gender_item = next(
                (item for item in genders if normalize_tnved_gender(item.get("name")) == normalized_gender),
                None,
            )
        return gender_item.get("codes") if gender_item else None
