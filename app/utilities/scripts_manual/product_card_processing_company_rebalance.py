"""Rebalance product card processing companies by current grouping rules.

Usage from Flask shell:
    from utilities.scripts_manual.product_card_processing_company_rebalance import (
        preview_rebalance_product_card_processing_companies,
        rebalance_product_card_processing_companies,
    )

    preview_rebalance_product_card_processing_companies()
    rebalance_product_card_processing_companies()
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from sqlalchemy.orm import selectinload

from config import settings
from models import (
    Clothes,
    Cosmetics,
    Linen,
    ModerationStatus,
    Parfum,
    ProductCard,
    Shoe,
    Socks,
    Toys,
    db,
)
from tezaurus.processing_companies import ProcessingCompaniesClient
from views.main.product_cards.support import _card_processing_country


DEFAULT_TARGET_STATUSES = (
    ModerationStatus.SENT,
    ModerationStatus.SENT_NO_RD,
    ModerationStatus.IN_PROGRESS,
    ModerationStatus.IN_MODERATION,
    ModerationStatus.CLARIFICATION,
    ModerationStatus.APPROVED,
    ModerationStatus.PARTIALLY_APPROVED,
)

LOG_NOTE = "служебное перераспределение компании по правилу клиент + категория + РФ/не РФ"
EXCLUDED_SOURCE_COMPANY_INNS = frozenset(("4400023120", "4400027438"))
EXCLUDED_SOURCE_COMPANY_TITLES = frozenset(("аврора", "ооо \"перемены\"", "перемены"))


def _status_value(status) -> str:
    return status.value if hasattr(status, "value") else str(status)


def _normalize_statuses(statuses=None) -> list[ModerationStatus]:
    raw_statuses = statuses or DEFAULT_TARGET_STATUSES
    return [
        status if isinstance(status, ModerationStatus) else ModerationStatus(status)
        for status in raw_statuses
    ]


def _company_key(card: ProductCard) -> tuple[str, str, str]:
    return (
        (card.processing_company_inn or "").strip(),
        (card.processing_company_external_id or "").strip(),
        (card.processing_company_title or "").strip(),
    )


def _has_company(card: ProductCard) -> bool:
    return any(_company_key(card))


def _company_label(card: ProductCard) -> str:
    inn, external_id, title = _company_key(card)
    return " ".join(part for part in (inn, title) if part) or external_id


def _is_excluded_source_company(card: ProductCard) -> bool:
    inn, _external_id, title = _company_key(card)
    normalized_title = " ".join(title.lower().replace("«", "\"").replace("»", "\"").split())
    return inn in EXCLUDED_SOURCE_COMPANY_INNS or normalized_title in EXCLUDED_SOURCE_COMPANY_TITLES


def _append_card_log(old: str | None, line: str) -> str:
    return ((old or "") + line)[-settings.ProducCards.MAX_LOG:]


def _load_cards(statuses=None) -> list[ProductCard]:
    return (
        ProductCard.query
        .options(
            selectinload(ProductCard.clothes).selectinload(Clothes.sizes_quantities),
            selectinload(ProductCard.socks).selectinload(Socks.sizes_quantities),
            selectinload(ProductCard.shoes).selectinload(Shoe.sizes_quantities),
            selectinload(ProductCard.linen).selectinload(Linen.sizes_quantities),
            selectinload(ProductCard.parfum),
            selectinload(ProductCard.cosmetics),
            selectinload(ProductCard.toys),
        )
        .filter(ProductCard.status.in_(_normalize_statuses(statuses)))
        .order_by(ProductCard.user_id.asc(), ProductCard.created_at.asc(), ProductCard.id.asc())
        .all()
    )


def _build_groups(cards: list[ProductCard]) -> tuple[dict[tuple[int, str, str], list[dict[str, Any]]], list[dict[str, Any]]]:
    client = ProcessingCompaniesClient()
    groups: dict[tuple[int, str, str], list[dict[str, Any]]] = {}
    skipped: list[dict[str, Any]] = []

    for card in cards:
        country = _card_processing_country(card)
        if not card.user_id:
            skipped.append({"card_id": card.id, "reason": "нет user_id"})
            continue
        if not country:
            skipped.append({"card_id": card.id, "reason": "не указана страна"})
            continue

        try:
            processing_request = client.build_request(category=card.category, country=country)
        except ValueError as exc:
            skipped.append({"card_id": card.id, "reason": str(exc)})
            continue

        scope_key = (card.user_id, processing_request.category, processing_request.origin)
        groups.setdefault(scope_key, []).append({
            "card": card,
            "country": country,
            "request": processing_request,
        })

    return groups, skipped


def _canonical_card(group_items: list[dict[str, Any]]) -> ProductCard | None:
    candidates = [
        item["card"]
        for item in group_items
        if _has_company(item["card"]) and not _is_excluded_source_company(item["card"])
    ]
    if not candidates:
        return None

    return sorted(
        candidates,
        key=lambda card: (
            card.processing_company_assigned_at or card.created_at or datetime.min,
            card.created_at or datetime.min,
            card.id or 0,
        ),
    )[0]


def _group_without_source_reason(group_items: list[dict[str, Any]]) -> str:
    if any(_has_company(item["card"]) for item in group_items):
        return "нет доступной фирмы: все закрепленные фирмы исключены из выбора основной"
    return "нет ни одной закрепленной фирмы"


def _excluded_source_card_ids(group_items: list[dict[str, Any]]) -> list[int]:
    return [
        item["card"].id
        for item in group_items
        if _has_company(item["card"]) and _is_excluded_source_company(item["card"])
    ]


def _needs_company_update(card: ProductCard, source: ProductCard, processing_request) -> bool:
    return (
        _company_key(card) != _company_key(source)
        or (card.processing_company_origin or "") != processing_request.origin
        or (card.processing_company_category or "") != processing_request.category
    )


def _build_change(item: dict[str, Any], source: ProductCard) -> dict[str, Any] | None:
    card = item["card"]
    processing_request = item["request"]
    if not _needs_company_update(card, source, processing_request):
        return None

    old_status = _status_value(card.status)
    new_status = (
        ModerationStatus.IN_MODERATION.value
        if card.status == ModerationStatus.APPROVED
        else old_status
    )

    return {
        "card_id": card.id,
        "user_id": card.user_id,
        "status": old_status,
        "new_status": new_status,
        "approved_reset": old_status != new_status,
        "category": card.category,
        "country": item["country"],
        "scope_category": processing_request.category,
        "scope_origin": processing_request.origin,
        "source_card_id": source.id,
        "old_company": {
            "inn": (card.processing_company_inn or "").strip(),
            "external_id": (card.processing_company_external_id or "").strip(),
            "title": (card.processing_company_title or "").strip(),
            "label": _company_label(card),
        },
        "new_company": {
            "inn": (source.processing_company_inn or "").strip(),
            "external_id": (source.processing_company_external_id or "").strip(),
            "title": (source.processing_company_title or "").strip(),
            "label": _company_label(source),
        },
    }


def reset_card_approval_for_company_rebalance(card: ProductCard) -> None:
    card.approved_at = None
    for unit in card._all_moderation_units():
        if hasattr(unit, "is_approved"):
            unit.is_approved = False


def _collect_rebalance_plan(statuses=None) -> dict[str, Any]:
    groups, skipped = _build_groups(_load_cards(statuses=statuses))
    changes: list[dict[str, Any]] = []
    groups_without_company: list[dict[str, Any]] = []
    group_summaries: list[dict[str, Any]] = []

    for (user_id, category, origin), items in groups.items():
        source = _canonical_card(items)
        company_keys = sorted({
            _company_key(item["card"])
            for item in items
            if _has_company(item["card"])
        })

        if not source:
            groups_without_company.append({
                "user_id": user_id,
                "scope_category": category,
                "scope_origin": origin,
                "card_ids": [item["card"].id for item in items],
                "excluded_source_card_ids": _excluded_source_card_ids(items),
                "reason": _group_without_source_reason(items),
            })
            continue

        group_changes = [
            change
            for item in items
            for change in (_build_change(item, source),)
            if change
        ]
        changes.extend(group_changes)
        group_summaries.append({
            "user_id": user_id,
            "scope_category": category,
            "scope_origin": origin,
            "card_count": len(items),
            "source_card_id": source.id,
            "source_company": _company_label(source),
            "distinct_company_count": len(company_keys),
            "change_count": len(group_changes),
        })

    return {
        "target_statuses": [_status_value(status) for status in _normalize_statuses(statuses)],
        "group_count": len(groups),
        "groups_with_changes_count": sum(1 for group in group_summaries if group["change_count"]),
        "groups_without_company_count": len(groups_without_company),
        "change_count": len(changes),
        "changes": changes,
        "groups": group_summaries,
        "groups_without_company": groups_without_company,
        "skipped_cards": skipped,
    }


def preview_rebalance_product_card_processing_companies(statuses=None) -> dict[str, Any]:
    """Preview product cards whose processing company will be changed."""
    return _collect_rebalance_plan(statuses=statuses)


def _apply_company_change(card: ProductCard, source: ProductCard, processing_request, *, now: datetime) -> None:
    old_label = _company_label(card) or "-"
    new_label = _company_label(source) or "-"
    was_approved = card.status == ModerationStatus.APPROVED

    card.processing_info = (source.processing_info or new_label)[:100]
    card.processing_company_external_id = source.processing_company_external_id or ""
    card.processing_company_title = source.processing_company_title or ""
    card.processing_company_inn = source.processing_company_inn or ""
    card.processing_company_origin = processing_request.origin[:20]
    card.processing_company_category = processing_request.category[:50]
    card.processing_company_payload = {
        "rebalance_from_card_id": source.id,
        "rebalanced_at": now.isoformat(),
        "request": processing_request.as_payload(),
        "source_payload": deepcopy(source.processing_company_payload),
    }
    card.processing_company_assigned_at = now

    status_note = ""
    if was_approved:
        reset_card_approval_for_company_rebalance(card)
        card.status = ModerationStatus.IN_MODERATION
        card.moderation_at = now
        status_note = " карточка переведена из approved в in_moderation, approved-метки сброшены;"

    card.card_log = _append_card_log(
        card.card_log,
        f"\n{now:%d.%m.%Y %H:%M} {LOG_NOTE}: {old_label} -> {new_label};{status_note}",
    )


def rebalance_product_card_processing_companies(
    *,
    commit: bool = True,
    statuses=None,
) -> dict[str, Any]:
    """Apply company rebalance without changing product card statuses."""
    groups, skipped = _build_groups(_load_cards(statuses=statuses))
    now = datetime.now()
    updated_ids: list[int] = []
    approved_reset_ids: list[int] = []
    groups_without_company: list[dict[str, Any]] = []

    try:
        for (user_id, category, origin), items in groups.items():
            source = _canonical_card(items)
            if not source:
                groups_without_company.append({
                    "user_id": user_id,
                    "scope_category": category,
                    "scope_origin": origin,
                    "card_ids": [item["card"].id for item in items],
                    "excluded_source_card_ids": _excluded_source_card_ids(items),
                    "reason": _group_without_source_reason(items),
                })
                continue

            for item in items:
                card = item["card"]
                processing_request = item["request"]
                if not _needs_company_update(card, source, processing_request):
                    continue

                was_approved = card.status == ModerationStatus.APPROVED
                _apply_company_change(card, source, processing_request, now=now)
                updated_ids.append(card.id)
                if was_approved:
                    approved_reset_ids.append(card.id)

        if commit:
            db.session.commit()
        else:
            db.session.flush()
            db.session.rollback()

        return {
            "target_statuses": [_status_value(status) for status in _normalize_statuses(statuses)],
            "updated_count": len(updated_ids),
            "updated_ids": updated_ids,
            "approved_reset_count": len(approved_reset_ids),
            "approved_reset_ids": approved_reset_ids,
            "groups_without_company_count": len(groups_without_company),
            "groups_without_company": groups_without_company,
            "skipped_cards": skipped,
            "committed": commit,
            "rolled_back": not commit,
        }
    except Exception:
        db.session.rollback()
        raise
