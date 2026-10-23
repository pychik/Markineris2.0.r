"""Наполнение реестра РД историей: РД, которые операторы вводили в карточки товаров.

Запуск из flask shell:
    from utilities.scripts_manual.rd_registry_backfill import preview_rd_registry_backfill, backfill_rd_registry, \
        fill_rd_registry_countries

    preview_rd_registry_backfill()
    backfill_rd_registry()

После добавления страны в реестр сначала fill_rd_registry_countries(), затем backfill_rd_registry().
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime

from sqlalchemy import func, literal, select, union_all
from sqlalchemy.dialects.postgresql import insert

from models import ModerationStatus, ProductCard, User, db
from rd_registry.models import RdRegistryEntry
from rd_registry.normalize import rd_key
from rd_registry.service import _clean_country, _clean_subcategory, category_label
from views.main.product_cards.support import CATEGORIES_COMMON

# Строки правки карточки из h_update_product_card (пишутся с 13.04.2026, вторая - с 25.09.2026):
#   "13-04-2026 14:20:10 manager_login исправил (ОБРД): Страна, РД;"
#   "13-04-2026 14:20:10 manager_login установил РД оператором (ОБРД);"
# Правку клиента пишут как "Клиент <login> исправил (НУ): РД;". Статус «Отправлена без РД» виден только
# по метке ОБРД в этих строках, отдельной истории статусов у карточки нет.
EDIT_LINE = re.compile(
    r"^(?P<at>\d\d-\d\d-\d{4} \d\d:\d\d:\d\d) (?P<actor>.+?) "
    r"(?:исправил \((?P<label>[^)]*)\): (?P<fields>[^;]*)|установил РД оператором \((?P<op_label>[^)]*)\))"
)
CLIENT_PREFIX = "Клиент "
SAMPLE_SIZE = 10


def last_rd_edit(card_log: str | None) -> tuple[datetime, str, str] | None:
    """Последняя правка РД по логу карточки: (когда, кто, метка статуса) или None."""
    last = None
    for line in (card_log or "").splitlines():
        m = EDIT_LINE.match(line)
        if not m:
            continue
        if m["fields"] is not None and "РД" not in {f.strip() for f in m["fields"].split(",")}:
            continue
        label = m["op_label"] if m["fields"] is None else m["label"]
        last = (datetime.strptime(m["at"], "%d-%m-%Y %H:%M:%S"), m["actor"], label)
    return last


def _card_rd_rows():
    """Позиции карточек с РД (дата РД заполнена, как в card_has_rd) вместе с данными карточки."""
    parts = []
    for cfg in CATEGORIES_COMMON.values():
        model = getattr(ProductCard, cfg["rel_name"]).property.mapper.class_
        subcategory = model.__table__.c.get("subcategory")
        parts.append(
            select(
                model.card_id, model.rd_type, model.rd_name, model.rd_date, model.rd_date_to, model.tnved_code,
                model.country,
                (subcategory if subcategory is not None else literal(None, db.String)).label("subcategory"),
            ).where(model.card_id.isnot(None), model.rd_date.isnot(None))
        )
    positions = union_all(*parts).subquery()
    return db.session.execute(
        select(positions, ProductCard.category, ProductCard.status, ProductCard.sent_at,
               ProductCard.created_at, ProductCard.card_log)
        .join(ProductCard, ProductCard.id == positions.c.card_id)
    ).all()


def _rd_of(row) -> tuple:
    return rd_key(row.rd_name), row.rd_date, row.rd_date_to


def collect_operator_rds(include_same_rd: bool = False) -> tuple[dict, Counter]:
    """Будущие записи реестра {ключ уникальности реестра: данные} и счётчики по карточкам."""
    stats = Counter()
    rows = []
    for row in _card_rd_rows():
        if row.status == ModerationStatus.REJECTED:
            stats["rejected_skipped"] += 1
        else:
            rows.append(row)

    ours = {}
    for row in rows:
        edit = last_rd_edit(row.card_log)
        if edit and not edit[1].startswith(CLIENT_PREFIX):
            ours[row.card_id] = edit
            stats[f"operator ({edit[2] or 'без метки'})"] += 1
        elif edit:
            stats["client_last_skipped"] += 1
    our_rds = {_rd_of(row) for row in rows if row.card_id in ours}

    entries = {}
    for row in rows:
        if row.card_id in ours:
            used_at, login, _ = ours[row.card_id]
        elif _rd_of(row) in our_rds:
            stats["same_rd_cards"] += 1
            if not include_same_rd:
                continue
            used_at, login = row.sent_at or row.created_at or datetime.now(), None
        else:
            continue

        key = rd_key(row.rd_name)
        if not (row.rd_type and key and row.rd_date_to):  # как в remember_rd
            continue
        subcategory = _clean_subcategory(row.category, row.subcategory)
        unique = (key, row.rd_date, row.rd_date_to, row.category, subcategory, (row.tnved_code or "").strip(),
                  _clean_country(row.country))
        entry = entries.setdefault(unique, {"card_ids": set(), "first": (used_at, login), "last": (used_at, row)})
        entry["card_ids"].add(row.card_id)
        if used_at < entry["first"][0]:
            entry["first"] = (used_at, login)
        if used_at >= entry["last"][0]:
            entry["last"] = (used_at, row)
    stats["cards_with_rd"] = len(rows) + stats["rejected_skipped"]
    return entries, stats


def _summary(entries: dict, stats: Counter) -> dict:
    existing = {tuple(r) for r in db.session.execute(select(
        RdRegistryEntry.search_key, RdRegistryEntry.rd_date, RdRegistryEntry.rd_date_to,
        RdRegistryEntry.category, RdRegistryEntry.subcategory, RdRegistryEntry.tnved_code, RdRegistryEntry.country,
    )).all()}
    new_count = sum(1 for unique in entries if unique not in existing)
    top = sorted(entries.items(), key=lambda item: -len(item[1]["card_ids"]))[:SAMPLE_SIZE]
    return {
        **dict(stats),
        "entries": len(entries),
        "new_entries": new_count,
        "existing_entries": len(entries) - new_count,
        "distinct_rds": len({unique[:3] for unique in entries}),
        "expired_entries": sum(1 for unique in entries if unique[2] < date.today()),
        "sample": [
            {
                "rd_name": entry["last"][1].rd_name,
                "rd_date": f"{unique[1]:%d.%m.%Y}-{unique[2]:%d.%m.%Y}",
                "category": category_label(unique[3], unique[4]),
                "tnved_code": unique[5],
                "country": unique[6],
                "cards": len(entry["card_ids"]),
            }
            for unique, entry in top
        ],
    }


def preview_rd_registry_backfill(include_same_rd: bool = False) -> dict:
    """Что запишет backfill_rd_registry, без изменений в БД."""
    return _summary(*collect_operator_rds(include_same_rd))


def backfill_rd_registry(include_same_rd: bool = False) -> dict:
    """Пишет РД операторов в реестр и коммитит. Повторный запуск ничего не дублирует.

    Новая запись: usage_count = число карточек, created_at/created_by - первая правка оператора,
    last_used_at - последняя. У существующей записи растут только usage_count и last_used_at (до большего
    из значений), архив и авторство не трогаем.
    """
    entries, stats = collect_operator_rds(include_same_rd)
    summary = _summary(entries, stats)
    if not entries:
        return summary

    logins = {entry["first"][1] for entry in entries.values() if entry["first"][1]}
    user_ids = dict(db.session.execute(
        select(User.login_name, func.min(User.id)).where(User.login_name.in_(logins)).group_by(User.login_name)
    ).all()) if logins else {}

    values = []
    for (key, rd_date, rd_date_to, category, subcategory, tnved_code, country), entry in entries.items():
        (created_at, login), (last_used_at, row) = entry["first"], entry["last"]
        values.append({
            "rd_type": row.rd_type,
            "rd_name": row.rd_name.replace("№", "").strip(),
            "rd_date": rd_date,
            "rd_date_to": rd_date_to,
            "search_key": key,
            "category": category,
            "subcategory": subcategory,
            "tnved_code": tnved_code,
            "country": country,
            "usage_count": len(entry["card_ids"]),
            "created_by_id": user_ids.get(login),
            "created_at": created_at,
            "last_used_at": last_used_at,
        })
    stmt = insert(RdRegistryEntry).values(values)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_rd_registry_key_dates_category_tnved_country",
        set_={
            "usage_count": func.greatest(RdRegistryEntry.usage_count, stmt.excluded.usage_count),
            "last_used_at": func.greatest(RdRegistryEntry.last_used_at, stmt.excluded.last_used_at),
        },
    )
    try:
        db.session.execute(stmt)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return summary


def fill_rd_registry_countries() -> dict:
    """Проставляет страну записям реестра, внесённым до появления поля. Коммитит.

    Страну берём у карточек с этим РД (ключ реестра без страны). Если карточки с ним есть на разные страны,
    запись получает самую частую, остальные допишет backfill_rd_registry() отдельными записями. Записи
    без карточек (добавлены вручную) и те, чья пара уже есть в реестре со страной, остаются без страны:
    их правят на странице реестра, фильтр «Без страны».
    """
    entries, _ = collect_operator_rds(include_same_rd=True)
    countries_by_key: dict[tuple, Counter] = {}
    for unique, entry in entries.items():
        if unique[6]:
            countries_by_key.setdefault(unique[:6], Counter())[unique[6]] += len(entry["card_ids"])

    taken = {tuple(r) for r in db.session.execute(select(
        RdRegistryEntry.search_key, RdRegistryEntry.rd_date, RdRegistryEntry.rd_date_to,
        RdRegistryEntry.category, RdRegistryEntry.subcategory, RdRegistryEntry.tnved_code, RdRegistryEntry.country,
    ).where(RdRegistryEntry.country != "")).all()}
    rows = db.session.execute(select(RdRegistryEntry).where(RdRegistryEntry.country == "")).scalars().all()

    stats = Counter(without_country=len(rows))
    for row in rows:
        key = (row.search_key, row.rd_date, row.rd_date_to, row.category, row.subcategory, row.tnved_code)
        countries = countries_by_key.get(key)
        if not countries:
            stats["no_cards"] += 1
            continue
        country = countries.most_common(1)[0][0]
        if key + (country,) in taken:
            stats["already_with_country"] += 1
            continue
        row.country = country
        taken.add(key + (country,))
        stats["filled"] += 1
    db.session.commit()
    return dict(stats)
