from typing import Tuple

from utilities.categories_data.clothes_common.clothes_common_tnved_by_gender import CLOTHES_TNVED_DICT


VISIBLE_TO_RAW = {
    "Жен.": "ЖЕНСКИЙ",
    "Муж.": "МУЖСКОЙ",
    "Унисекс": "УНИВЕРСАЛЬНЫЙ (УНИСЕКС)",
    "Детск.": "БЕЗ УКАЗАНИЯ ПОЛА",      # по правилу: Детск = без указания пола
    "Без указания пола": "БЕЗ УКАЗАНИЯ ПОЛА",
}


def _normalize_kind(s: str) -> str:
    return str(s).strip().upper()


def _normalize_gender_label(g: str) -> str:
    g = str(g).strip()
    # приводим к одному из видимых ярлыков, важна замена «Детск.»
    if g == "Детск.":
        return "Без указания пола"
    return g


def _pairs_backup_only(entry) -> Tuple[Tuple[str, str], ...]:
    """Оставить только запасные пары: пары минус те, чьи коды входят в primary_codes."""
    if not entry:
        return ()
    primary_codes, pairs = entry
    prim_set = set(primary_codes or ())
    return tuple((c, d) for (c, d) in (pairs or ()) if c not in prim_set)


def get_tnved_gender_clothes_common(type_name: str, gender: str, data=None) -> Tuple[Tuple[str, str], ...]:
    """
    Вернёт кортеж (код, описание).
    - Если по (тип, пол) есть основные коды -> (все основные + все запасные, без дублей, в нужном порядке).
    - Если основных нет -> только запасные.
    - Если записи по (тип, пол) нет -> запасные из 'Без указания пола';
      если и там нет -> объединённые запасные по всем полам для данного типа.
    """
    data = data or CLOTHES_TNVED_DICT

    t = _normalize_kind(type_name)
    g = _normalize_gender_label(gender)

    type_bucket = data.get(t, {})
    entry = type_bucket.get(g)

    # 1) Есть запись по полу
    if entry:
        primary_codes, pairs = entry
        if primary_codes:  # вернуть основные + запасные (pairs уже у нас "primary сначала, потом backup")
            # pairs уже без дублей и в порядке (мы так строили структуру)
            return tuple(pairs or ())
        # основных нет — вернуть только запасные
        return _pairs_backup_only(entry)

    # 2) Нет записи по полу — пробуем 'Без указания пола'
    entry_any = type_bucket.get("Без указания пола")
    if entry_any:
        return _pairs_backup_only(entry_any)

    # 3) Вообще нет записи под этим полом — соберём запасные из всех веток этого типа
    seen = set()
    merged = []
    for _g, _entry in type_bucket.items():
        for c, d in _pairs_backup_only(_entry):
            if c not in seen:
                merged.append((c, d))
                seen.add(c)
    return tuple(merged)


def get_tnved_codes_for_gender(type_name: str, gender: str, data=None) -> list[str]:
    """
    Вернёт список номеров ТН ВЭД для конкретных (тип, пол):
      - основные + запасные для этого же пола;
      - без дублей, без фолбэков.
    """
    data = data or CLOTHES_TNVED_DICT
    t = _normalize_kind(type_name)
    g = _normalize_gender_label(gender)

    entry = data.get(t, {}).get(g)
    if not entry:
        return []

    primary_codes, pairs = entry
    out = list(primary_codes or [])
    seen = set(out)

    # добавляем коды из pairs, которых ещё нет
    out.extend([c for c, _ in (pairs or ()) if c not in seen])
    return out


# search_description = get_tnved_gender_clothes_common(type_name="блузка", gender='Жен.')
# print(search_description)
# print(get_tnved_codes_for_gender(type_name="блузка", gender='Жен.'))