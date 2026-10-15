"""Backfill ordinary-order company and UPD fields after a Flask-Migrate revision.

From ``flask shell`` after applying the schema migration::

    from utilities.scripts_manual.backfill_order_processing_info import backfill_order_processing_info
    backfill_order_processing_info()              # preview, no writes
    backfill_order_processing_info(commit=True)   # apply in batches

The script leaves ambiguous or conflicting legacy text untouched.
"""

from sqlalchemy import select, update

from models import Order, db
from utilities.order_processing_info import parse_single_processing_info
from views.crm.schema import CompaniesOperators


COMPANY_KEYS = {company.as_option()[1]: f"g:{company.name}" for company in CompaniesOperators}


def backfill_order_processing_info(*, commit: bool = False, batch_size: int = 500) -> dict:
    """Preview or fill only missing fields on ordinary orders with one parsed UPD."""
    if batch_size < 1:
        raise ValueError("batch_size должен быть больше нуля")

    result = {"scanned": 0, "parsed": 0, "unparseable": 0, "conflicts": 0,
              "already_filled": 0, "would_update": 0, "updated": 0,
              "unknown_company_key": 0, "unparseable_ids": [], "conflict_ids": []}
    last_id = 0
    try:
        return _backfill_batches(result, last_id=last_id, batch_size=batch_size, commit=commit)
    except Exception:
        db.session.rollback()
        raise


def _backfill_batches(result: dict, *, last_id: int, batch_size: int, commit: bool) -> dict:
    while True:
        batch = db.session.execute(
            select(Order.id, Order.processing_info, Order.processing_company_key,
                   Order.processing_company_label, Order.upd_number)
            .where(Order.id > last_id, Order.is_moderation.is_(False),
                   Order.processing_info.contains("УПД:"))
            .order_by(Order.id).limit(batch_size)
        ).all()
        if not batch:
            break

        for row in batch:
            last_id = row.id
            result["scanned"] += 1
            parsed = parse_single_processing_info(row.processing_info)
            if not parsed:
                result["unparseable"] += 1
                if len(result["unparseable_ids"]) < 20:
                    result["unparseable_ids"].append(row.id)
                continue

            result["parsed"] += 1
            company_label, upd_number = parsed
            company_key = COMPANY_KEYS.get(company_label)
            if not company_key:
                result["unknown_company_key"] += 1
            if ((row.processing_company_label and row.processing_company_label != company_label) or
                (row.upd_number and row.upd_number != upd_number) or
                (row.processing_company_key and company_key and row.processing_company_key != company_key)):
                result["conflicts"] += 1
                if len(result["conflict_ids"]) < 20:
                    result["conflict_ids"].append(row.id)
                continue

            values = {}
            if not row.processing_company_label:
                values["processing_company_label"] = company_label
            if not row.upd_number:
                values["upd_number"] = upd_number
            if not row.processing_company_key and company_key:
                values["processing_company_key"] = company_key
            if not values:
                result["already_filled"] += 1
                continue

            result["would_update"] += 1
            if commit:
                db.session.execute(update(Order).where(Order.id == row.id).values(**values))
                result["updated"] += 1

        if commit:
            db.session.commit()

    return result
