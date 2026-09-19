"""Assign Tezaurus companies for groups stuck on excluded companies.

Usage from Flask shell:
    from utilities.scripts_manual.product_card_processing_company_excluded_tezaurus import (
        preview_assign_excluded_product_card_companies_from_tezaurus,
        assign_excluded_product_card_companies_from_tezaurus,
    )

    preview_assign_excluded_product_card_companies_from_tezaurus()
    assign_excluded_product_card_companies_from_tezaurus()
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models import ModerationStatus, ProductCard, db
from tezaurus.processing_companies import ProcessingCompaniesClient
from utilities.scripts_manual.product_card_processing_company_rebalance import (
    EXCLUDED_SOURCE_COMPANY_INNS,
    EXCLUDED_SOURCE_COMPANY_TITLES,
    _append_card_log,
    _build_groups,
    _canonical_card,
    _company_label,
    _excluded_source_card_ids,
    _load_cards,
    _normalize_statuses,
    _status_value,
    reset_card_approval_for_company_rebalance,
)
from views.main.product_cards.support import (
    _find_processing_company_payload,
    _processing_company_value,
    _save_card_processing_company,
)


LOG_NOTE = "служебная замена исключенной фирмы через Tezaurus"


def _normalize_company_title(title: str) -> str:
    return " ".join((title or "").lower().replace("«", "\"").replace("»", "\"").split())


def _is_excluded_company_payload(company: dict[str, Any]) -> bool:
    inn = _processing_company_value(company, "inn", "company_idn")
    title = _processing_company_value(company, "title", "name", "company_name")
    return inn in EXCLUDED_SOURCE_COMPANY_INNS or _normalize_company_title(title) in EXCLUDED_SOURCE_COMPANY_TITLES


def _target_groups(statuses=None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups, skipped = _build_groups(_load_cards(statuses=statuses))
    target_groups: list[dict[str, Any]] = []

    for (user_id, category, origin), items in groups.items():
        if _canonical_card(items):
            continue

        excluded_card_ids = _excluded_source_card_ids(items)
        if not excluded_card_ids:
            continue

        target_groups.append({
            "user_id": user_id,
            "scope_category": category,
            "scope_origin": origin,
            "card_ids": [item["card"].id for item in items],
            "excluded_card_ids": excluded_card_ids,
            "statuses": sorted({_status_value(item["card"].status) for item in items}),
            "request": items[0]["request"],
            "items": items,
        })

    return target_groups, skipped


def preview_assign_excluded_product_card_companies_from_tezaurus(statuses=None) -> dict[str, Any]:
    target_groups, skipped = _target_groups(statuses=statuses)

    return {
        "target_statuses": [_status_value(status) for status in _normalize_statuses(statuses)],
        "group_count": len(target_groups),
        "card_count": sum(len(group["card_ids"]) for group in target_groups),
        "excluded_card_count": sum(len(group["excluded_card_ids"]) for group in target_groups),
        "groups": [
            {
                "user_id": group["user_id"],
                "scope_category": group["scope_category"],
                "scope_origin": group["scope_origin"],
                "card_ids": group["card_ids"],
                "excluded_card_ids": group["excluded_card_ids"],
                "statuses": group["statuses"],
            }
            for group in target_groups
        ],
        "skipped_cards": skipped,
    }


def _apply_tezaurus_company(
    card: ProductCard,
    *,
    processing_request,
    response_payload: dict[str, Any],
    now: datetime,
) -> bool:
    old_label = _company_label(card) or "-"
    was_approved = card.status == ModerationStatus.APPROVED

    assigned = _save_card_processing_company(
        card,
        processing_request=processing_request,
        response_payload=response_payload,
        assigned_at=now,
    )

    status_note = ""
    if was_approved:
        reset_card_approval_for_company_rebalance(card)
        card.status = ModerationStatus.IN_MODERATION
        card.moderation_at = now
        status_note = " карточка переведена из approved в in_moderation, approved-метки сброшены;"

    card.card_log = _append_card_log(
        card.card_log,
        f"\n{now:%d.%m.%Y %H:%M} {LOG_NOTE}: {old_label} -> {assigned['label']};{status_note}",
    )
    return was_approved


def assign_excluded_product_card_companies_from_tezaurus(
    *,
    commit: bool = True,
    statuses=None,
    client: ProcessingCompaniesClient | None = None,
) -> dict[str, Any]:
    if not commit:
        preview = preview_assign_excluded_product_card_companies_from_tezaurus(statuses=statuses)
        return {
            "ok": False,
            "reason": "commit_false_does_not_call_tezaurus",
            "message": "Use preview for dry run. Tezaurus assignment is only executed with commit=True.",
            "preview": preview,
            "committed": False,
            "rolled_back": True,
        }

    target_groups, skipped = _target_groups(statuses=statuses)
    client = client or ProcessingCompaniesClient()
    now = datetime.now()
    updated_ids: list[int] = []
    approved_reset_ids: list[int] = []
    selected_companies: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    try:
        for group in target_groups:
            processing_request = group["request"]
            response_payload = client.select(
                category=processing_request.category,
                origin=processing_request.origin,
            )
            company = _find_processing_company_payload(response_payload)
            if not company:
                errors.append({
                    "user_id": group["user_id"],
                    "scope_category": group["scope_category"],
                    "scope_origin": group["scope_origin"],
                    "card_ids": group["card_ids"],
                    "reason": "Tezaurus returned no company",
                })
                continue
            if _is_excluded_company_payload(company):
                errors.append({
                    "user_id": group["user_id"],
                    "scope_category": group["scope_category"],
                    "scope_origin": group["scope_origin"],
                    "card_ids": group["card_ids"],
                    "reason": "Tezaurus returned excluded company",
                    "company": company,
                })
                continue

            selected_companies.append({
                "user_id": group["user_id"],
                "scope_category": group["scope_category"],
                "scope_origin": group["scope_origin"],
                "card_ids": group["card_ids"],
                "company": company,
            })

            for item in group["items"]:
                card = item["card"]
                was_approved = _apply_tezaurus_company(
                    card,
                    processing_request=processing_request,
                    response_payload=response_payload,
                    now=now,
                )
                updated_ids.append(card.id)
                if was_approved:
                    approved_reset_ids.append(card.id)

        if errors:
            db.session.rollback()
            return {
                "ok": False,
                "errors": errors,
                "updated_count": 0,
                "updated_ids": [],
                "approved_reset_count": 0,
                "approved_reset_ids": [],
                "committed": False,
                "rolled_back": True,
                "skipped_cards": skipped,
            }

        db.session.commit()

        return {
            "ok": True,
            "target_statuses": [_status_value(status) for status in _normalize_statuses(statuses)],
            "group_count": len(target_groups),
            "updated_count": len(updated_ids),
            "updated_ids": updated_ids,
            "approved_reset_count": len(approved_reset_ids),
            "approved_reset_ids": approved_reset_ids,
            "selected_companies": selected_companies,
            "skipped_cards": skipped,
            "committed": True,
            "rolled_back": False,
        }
    except Exception:
        db.session.rollback()
        raise
