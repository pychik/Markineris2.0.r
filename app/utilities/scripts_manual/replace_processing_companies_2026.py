"""Manual service transfer after the Tezaurus distribution change.

Import in ``flask shell``. Nothing is changed on import or by ``preview()``.
The caller must pass the exact card and order IDs from the reviewed preview to
``apply()``. Run this separately in each service; never share IDs across DBs.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, exists, or_

from config import settings
from models import Clothes, FastOrderCompanies, ModerationStatus, Order, OrderStat, Parfum, ProductCard, Shoe, db
from views.crm.crm_support import h_cancel_order_process_payment
from views.main.product_cards.crm.helpers import h_append_card_log


REASON = "Карточки товаров отправлены на повторную модерацию в связи со сменой компании проводчика"
COPY_BLOCK_MARKER = "[SERVICE_COMPANY_REPLACEMENT_2026]"
SOURCE_ISHMITOV = "023103006891"
SOURCE_KHUZIN = "023104386702"
TARGET_MINDIYAROV = ("022703451765", 'ИП "Миндияров Савелий Валерьевич"')
TARGET_MEKOSHKISHVILI = ("662906603013", 'ИП "Мекошкишвили Евгений Семенович"')


def _card_origin(card: ProductCard) -> str:
    origin = (card.processing_company_origin or "").lower().strip()
    if origin:
        return origin
    countries = {
        (item.country or "").upper().strip()
        for item in (card.clothes if card.category == "clothes" else [])
    }
    if countries == {"РОССИЯ"}:
        return "rf"
    if countries and "РОССИЯ" not in countries:
        return "import"
    return ""


def _rule(card: ProductCard):
    inn = (card.processing_company_inn or "").strip()
    if card.category in ("shoes", "parfum") and inn == SOURCE_ISHMITOV:
        return TARGET_MINDIYAROV
    if card.category == "clothes" and inn == SOURCE_KHUZIN and _card_origin(card) == "rf":
        return TARGET_MEKOSHKISHVILI
    return None


def _candidate_cards() -> list[tuple[ProductCard, tuple[str, str]]]:
    cards = ProductCard.query.filter(
        ProductCard.processing_company_inn.in_((SOURCE_ISHMITOV, SOURCE_KHUZIN)),
        ProductCard.category.in_(("shoes", "parfum", "clothes")),
        ProductCard.status != ModerationStatus.CREATED,
    ).order_by(ProductCard.id).all()
    return [(card, target) for card in cards if (target := _rule(card))]


def _candidate_orders() -> list[Order]:
    # Each GTIN order position retains its conductor through fast_order_company_id.
    # The position's card_id is intentionally blank after copying from the card.
    ishmitov_shoes = exists().where(
        Shoe.order_id == Order.id,
        Shoe.fast_order_company_id == FastOrderCompanies.id,
        FastOrderCompanies.order_id == Order.id,
        FastOrderCompanies.processing_company_inn == SOURCE_ISHMITOV,
    )
    ishmitov_parfum = exists().where(
        Parfum.order_id == Order.id,
        Parfum.fast_order_company_id == FastOrderCompanies.id,
        FastOrderCompanies.order_id == Order.id,
        FastOrderCompanies.processing_company_inn == SOURCE_ISHMITOV,
    )
    khuzin_rf = exists().where(
        Clothes.order_id == Order.id,
        Clothes.country.ilike("РОССИЯ"),
        Clothes.fast_order_company_id == FastOrderCompanies.id,
        FastOrderCompanies.order_id == Order.id,
        FastOrderCompanies.processing_company_inn == SOURCE_KHUZIN,
    )
    return Order.query.filter(
        Order.is_moderation.is_(True),
        Order.to_delete.is_(False),
        Order.stage != settings.OrderStage.CANCELLED,
        or_(
            and_(Order.category == settings.Shoes.CATEGORY, ishmitov_shoes),
            and_(Order.category == settings.Parfum.CATEGORY, ishmitov_parfum),
            and_(Order.category == settings.Clothes.CATEGORY, khuzin_rf),
        ),
    ).order_by(Order.id).all()


def _item_summary(item) -> dict:
    return {key: getattr(item, key, None) for key in
            ("id", "article", "type", "trademark", "country", "tnved_code")}


def _card_items(card: ProductCard) -> list:
    return getattr(card, card.category, [])


def _order_items(order: Order) -> list:
    return {settings.Shoes.CATEGORY: order.shoes,
            settings.Parfum.CATEGORY: order.parfum,
            settings.Clothes.CATEGORY: order.clothes}[order.category]


def _order_item_summaries(order: Order) -> list[dict]:
    companies = {company.id: company.processing_company_inn
                 for company in order.fast_order_companies}
    return [dict(_item_summary(item),
                 conductor_inn=companies.get(item.fast_order_company_id))
            for item in _order_items(order)]


def preview() -> dict:
    cards = _candidate_cards()
    orders = _candidate_orders()
    unresolved_clothes = ProductCard.query.filter(
        ProductCard.category == "clothes",
        ProductCard.processing_company_inn == SOURCE_KHUZIN,
        ProductCard.status != ModerationStatus.CREATED,
    ).order_by(ProductCard.id).all()
    return {
        "cards": [{"id": card.id, "user_id": card.user_id, "category": card.category,
                   "origin": _card_origin(card), "status": card.status.value,
                   "action": "delete" if card.status == ModerationStatus.REJECTED else "move_to_moderation",
                   "from_inn": card.processing_company_inn, "to_inn": target[0],
                   "items": [_item_summary(item) for item in _card_items(card)]}
                  for card, target in cards],
        "orders": [{"id": order.id, "order_idn": order.order_idn,
                    "user_id": order.user_id, "category": order.category,
                    "stage": order.stage, "payment": order.payment,
                    "items": _order_item_summaries(order)}
                   for order in orders],
        "card_ids": [card.id for card, _ in cards],
        "order_ids": [order.id for order in orders],
        "rejected_card_ids_to_delete": [card.id for card, _ in cards if card.status == ModerationStatus.REJECTED],
        "clothes_with_unknown_origin_ids": [card.id for card in unresolved_clothes if not _card_origin(card)],
    }


def apply(*, expected_card_ids: list[int], expected_order_ids: list[int]) -> dict:
    """Cancel selected GTIN orders first, then update cards in one transaction."""
    plan = preview()
    if plan["clothes_with_unknown_origin_ids"]:
        raise ValueError("Есть карточки одежды Хузина без определённого происхождения; разберите их до применения")
    if sorted(expected_card_ids) != plan["card_ids"] or sorted(expected_order_ids) != plan["order_ids"]:
        raise ValueError("Список карточек или заказов изменился; получите и проверьте новый preview")
    now = datetime.now()
    cards = _candidate_cards()
    orders = _candidate_orders()
    try:
        for order in orders:
            if order.payment:
                if not order.order_idn:
                    raise ValueError(f"Оплаченный заказ {order.id} без order_idn: безопасная отмена невозможна")
                stat = OrderStat.query.filter_by(order_idn=order.order_idn).one_or_none()
                if stat is None or stat.op_cost is None or not stat.marks_count:
                    raise ValueError(f"Заказ {order.id}: нет данных стоимости для возврата средств")
                h_cancel_order_process_payment(order_idn=order.order_idn, user_id=order.user_id)
                order.payment = False
            order.stage = settings.OrderStage.CANCELLED
            order.cc_created = now
            order.comment_cancel = f"{COPY_BLOCK_MARKER} {REASON}"

        for card, (inn, title) in cards:
            if card.status == ModerationStatus.REJECTED:
                db.session.delete(card)
                continue
            old_label = card.processing_company_label or card.processing_info or "—"
            old_status = card.status.value
            for unit in card._all_moderation_units():
                if hasattr(unit, "is_approved"):
                    unit.is_approved = False
            card.processing_company_inn = inn
            card.processing_company_title = title
            card.processing_company_external_id = ""
            card.processing_info = f"{inn} {title}"
            card.processing_company_assigned_at = now
            card.processing_company_payload = {
                "manual_change": True, "reason": REASON,
                "changed_at": now.isoformat(),
                "company": {"inn": inn, "title": title},
            }
            card.status = ModerationStatus.IN_MODERATION
            card.moderation_at = now
            card.approved_at = None
            card.rejected_at = None
            card.reject_reason = ""
            card.is_repeat_moderation = card.is_repeat_moderation or old_status in (
                ModerationStatus.APPROVED.value,
                ModerationStatus.PARTIALLY_APPROVED.value,
            )
            card.card_log = h_append_card_log(
                card.card_log,
                f"\n{now:%d.%m.%Y %H:%M:%S} Служебный перенос на повторную модерацию "
                f"в связи со сменой компании проводчика: {old_label} -> {inn} {title}; "
                f"статус {old_status} -> {card.status.value};",
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    deleted = set(plan["rejected_card_ids_to_delete"])
    return {
        "updated_card_ids": [card_id for card_id in plan["card_ids"] if card_id not in deleted],
        "deleted_rejected_card_ids": plan["rejected_card_ids_to_delete"],
        "cancelled_order_ids": plan["order_ids"],
    }
