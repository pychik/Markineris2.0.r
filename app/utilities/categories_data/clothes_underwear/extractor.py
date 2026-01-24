from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def extract_tnved_codes(obj: Any) -> list[str]:
    """
    Достаёт все ТНВЭД-коды (строки из цифр длиной 10) из словаря/списков/кортежей
    любой вложенности и возвращает уникальный отсортированный список.
    """
    found: set[str] = set()

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
            return

        # строки не "итерируем" как коллекции
        if isinstance(x, (list, tuple, set)):
            for item in x:
                walk(item)
            return

        if isinstance(x, str):
            s = x.strip()
            if s.isdigit() and len(s) == 10:
                found.add(s)

    walk(obj)
    return sorted(found)


def extract_type_genders(data: dict[str, Any]) -> dict[str, list[str]]:
    """
    Для каждого типа изделия (верхний уровень словаря)
    возвращает список полов, найденных во вложенных словарях.
    """
    result: dict[str, list[str]] = {}

    for item_type, value in data.items():
        if not isinstance(value, dict):
            continue

        genders = sorted(value.keys())
        result[item_type] = genders

    return result

# пример использования:
# codes = extract_tnved_codes(UNDERWEAR_TNVED_DICT)
# print(codes)
