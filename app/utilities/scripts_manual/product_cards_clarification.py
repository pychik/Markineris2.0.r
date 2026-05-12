"""Helpers to move product cards back to clarification from Flask shell.

Usage:
    from utilities.scripts_manual.product_cards_clarification import move_cards_to_clarification
    move_cards_to_clarification([9505, 9502, 9501, 9499, 9498, 9497, 9496, 9495])
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from models import ProductCard, ModerationStatus, db

MAX_CARD_LOG = 2000


def normalize_card_ids(card_ids: Iterable[int]) -> list[int]:
    """Return unique integer card ids preserving the input order."""
    normalized: list[int] = []
    seen: set[int] = set()

    for raw_id in card_ids:
        card_id = int(raw_id)
        if card_id in seen:
            continue
        seen.add(card_id)
        normalized.append(card_id)

    return normalized


def load_cards(card_ids: Iterable[int]) -> list[ProductCard]:
    """Load cards by ids."""
    normalized_ids = normalize_card_ids(card_ids)
    if not normalized_ids:
        return []
    return ProductCard.query.filter(ProductCard.id.in_(normalized_ids)).all()


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
    """Reset approval markers that should not stay set in clarification."""
    card.approved_at = None
    card.rejected_at = None
    card.reject_reason = ""

    for unit in iter_card_approval_units(card):
        if hasattr(unit, "is_approved"):
            unit.is_approved = False


def move_card_to_clarification(card: ProductCard, *, now: datetime | None = None, log_note: str | None = None) -> None:
    """Move a single card to clarification and update related fields."""
    now = now or datetime.now()
    log_note = log_note or "возврат из готовых в уточнение вручную"

    card.status = ModerationStatus.CLARIFICATION
    card.clarification_requested_at = now
    reset_card_approval(card)
    append_card_log(card, f"\n{now:%d-%m-%Y %H:%M:%S} {log_note};")


def move_cards_to_clarification(card_ids: Iterable[int], *, commit: bool = True, log_note: str | None = None) -> dict:
    """Move product cards to clarification by ids.

    Args:
        card_ids: Iterable with product card ids.
        commit: Commit the transaction when True.
        log_note: Optional custom log text appended to `card_log`.

    Returns:
        Dict with updated and missing ids.
    """
    normalized_ids = normalize_card_ids(card_ids)
    now = datetime.now()
    cards = load_cards(normalized_ids)
    found_ids = {card.id for card in cards}

    for card in cards:
        move_card_to_clarification(card, now=now, log_note=log_note)

    if commit:
        db.session.commit()

    return {
        "updated": [card_id for card_id in normalized_ids if card_id in found_ids],
        "missing": [card_id for card_id in normalized_ids if card_id not in found_ids],
    }
