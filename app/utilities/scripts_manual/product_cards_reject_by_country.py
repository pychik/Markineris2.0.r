"""Reject product cards by country from Flask shell.

Usage:
    from utilities.scripts_manual.product_cards_reject_by_country import (
        preview_reject_product_cards_by_country,
        reject_product_cards_by_country,
    )

    preview_reject_product_cards_by_country()
    reject_product_cards_by_country()

    preview_reject_product_cards_by_country(country="РОССИЯ")
    reject_product_cards_by_country(country="РОССИЯ", commit=True)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from models import Clothes, Linen, ModerationStatus, Parfum, ProductCard, Shoe, Socks, db

MAX_CARD_LOG = 2000
DEFAULT_COUNTRY = "РОССИЯ"
DEFAULT_REJECT_REASON = "ОТМЕНА МОДЕРАЦИИ СОГЛАСНО НОВЫМ ПРАВИЛАМ ЧЗ"
DEFAULT_LOG_NOTE = "отмена сервером"


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().upper()


def _country_match_expr(column, country: str):
    return func.upper(func.trim(column)) == _normalize_text(country)


def _build_country_query(country: str):
    return (
        ProductCard.query
        .options(
            joinedload(ProductCard.clothes).joinedload(Clothes.sizes_quantities),
            joinedload(ProductCard.socks).joinedload(Socks.sizes_quantities),
            joinedload(ProductCard.shoes).joinedload(Shoe.sizes_quantities),
            joinedload(ProductCard.linen).joinedload(Linen.sizes_quantities),
            joinedload(ProductCard.parfum),
        )
        .filter(
            or_(
                ProductCard.clothes.any(_country_match_expr(Clothes.country, country)),
                ProductCard.socks.any(_country_match_expr(Socks.country, country)),
                ProductCard.shoes.any(_country_match_expr(Shoe.country, country)),
                ProductCard.linen.any(_country_match_expr(Linen.country, country)),
                ProductCard.parfum.any(_country_match_expr(Parfum.country, country)),
            )
        )
        .order_by(ProductCard.id.asc())
    )


def load_cards_by_country(country: str = DEFAULT_COUNTRY) -> list[ProductCard]:
    """Load all product cards that contain the specified country."""
    return _build_country_query(country).all()


def append_card_log(card: ProductCard, message: str) -> None:
    """Append a maintenance log message to the card log."""
    card.card_log = ((card.card_log or "") + message)[-MAX_CARD_LOG:]


def iter_card_approval_units(card: ProductCard):
    """Yield moderation units with `is_approved` for all supported categories."""
    for item in getattr(card, "clothes", []):
        for size in item.sizes_quantities:
            yield size

    for item in getattr(card, "socks", []):
        for size in item.sizes_quantities:
            yield size

    for item in getattr(card, "shoes", []):
        for size in item.sizes_quantities:
            yield size

    for item in getattr(card, "linen", []):
        for size in item.sizes_quantities:
            yield size

    for parfum in getattr(card, "parfum", []):
        yield parfum


def reset_card_approval(card: ProductCard) -> None:
    """Reset approval markers that should not stay set on rejected cards."""
    card.approved_at = None

    for unit in iter_card_approval_units(card):
        if hasattr(unit, "is_approved"):
            unit.is_approved = False


def _card_country_values(card: ProductCard) -> list[str]:
    values: list[str] = []

    for item in getattr(card, "clothes", []):
        if item.country:
            values.append(item.country)

    for item in getattr(card, "socks", []):
        if item.country:
            values.append(item.country)

    for item in getattr(card, "shoes", []):
        if item.country:
            values.append(item.country)

    for item in getattr(card, "linen", []):
        if item.country:
            values.append(item.country)

    for item in getattr(card, "parfum", []):
        if item.country:
            values.append(item.country)

    return values


def _is_card_already_rejected_by_rule(
    card: ProductCard,
    reject_reason: str,
) -> bool:
    has_approved_units = any(
        getattr(unit, "is_approved", False)
        for unit in iter_card_approval_units(card)
    )
    return (
        card.status == ModerationStatus.REJECTED
        and (card.reject_reason or "") == reject_reason
        and card.rejected_at is not None
        and card.approved_at is None
        and not has_approved_units
    )


def reject_card(
    card: ProductCard,
    *,
    now: datetime | None = None,
    reject_reason: str = DEFAULT_REJECT_REASON,
    log_note: str = DEFAULT_LOG_NOTE,
) -> bool:
    """Reject a single product card and update related fields.

    Returns True when the card was changed, False when it was already compliant.
    """
    now = now or datetime.now()
    if _is_card_already_rejected_by_rule(card, reject_reason):
        return False

    reset_card_approval(card)
    card.status = ModerationStatus.REJECTED
    card.reject_reason = reject_reason
    card.rejected_at = now
    append_card_log(
        card,
        f"\n{now:%d-%m-%Y %H:%M:%S} {log_note}; причина: {reject_reason};",
    )
    return True


def _build_preview_row(card: ProductCard) -> dict[str, Any]:
    return {
        "id": card.id,
        "status": card.status.value if hasattr(card.status, "value") else str(card.status),
        "category": card.category,
        "countries": _card_country_values(card),
        "reject_reason": card.reject_reason or "",
    }


def preview_reject_product_cards_by_country(
    country: str = DEFAULT_COUNTRY,
    *,
    reject_reason: str = DEFAULT_REJECT_REASON,
) -> dict[str, Any]:
    """Preview product cards that will be rejected by country."""
    cards = load_cards_by_country(country)
    already_rejected = [
        card.id for card in cards
        if _is_card_already_rejected_by_rule(card, reject_reason)
    ]
    to_update = [
        card.id for card in cards
        if card.id not in already_rejected
    ]
    return {
        "country": country,
        "total_found": len(cards),
        "to_update_count": len(to_update),
        "already_rejected_count": len(already_rejected),
        "to_update_ids": to_update,
        "already_rejected_ids": already_rejected,
        "cards": [_build_preview_row(card) for card in cards],
    }


def reject_product_cards_by_country(
    country: str = DEFAULT_COUNTRY,
    *,
    commit: bool = True,
    reject_reason: str = DEFAULT_REJECT_REASON,
    log_note: str = DEFAULT_LOG_NOTE,
) -> dict[str, Any]:
    """Reject all product cards that contain the specified country."""
    cards = load_cards_by_country(country)
    now = datetime.now()
    updated_ids: list[int] = []
    skipped_ids: list[int] = []

    for card in cards:
        changed = reject_card(
            card,
            now=now,
            reject_reason=reject_reason,
            log_note=log_note,
        )
        if changed:
            updated_ids.append(card.id)
        else:
            skipped_ids.append(card.id)

    if commit:
        db.session.commit()

    return {
        "country": country,
        "updated_count": len(updated_ids),
        "skipped_count": len(skipped_ids),
        "updated_ids": updated_ids,
        "skipped_ids": skipped_ids,
    }
