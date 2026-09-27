from datetime import date, datetime

from sqlalchemy import func, or_

from logger import logger
from models import db, ProductCard, ProductCardCompanyStatsSnapshot


def save_product_card_company_stats_snapshot(
    snapshot_date: date | None = None,
    snapshot_hour: int | None = None,
) -> dict[str, int | str]:
    now = datetime.now()
    snapshot_date = snapshot_date or date.today()
    snapshot_hour = now.hour if snapshot_hour is None else int(snapshot_hour)

    has_company = or_(
        func.coalesce(ProductCard.processing_company_inn, "") != "",
        func.coalesce(ProductCard.processing_company_external_id, "") != "",
        func.coalesce(ProductCard.processing_company_title, "") != "",
    )

    rows = (
        db.session.query(
            func.coalesce(ProductCard.processing_company_external_id, "").label("external_id"),
            func.coalesce(ProductCard.processing_company_title, "").label("title"),
            func.coalesce(ProductCard.processing_company_inn, "").label("inn"),
            func.coalesce(ProductCard.processing_company_category, "").label("category"),
            func.coalesce(ProductCard.processing_company_origin, "").label("origin"),
            ProductCard.status.label("status"),
            func.count(ProductCard.id).label("cards_count"),
        )
        .filter(has_company)
        .group_by(
            func.coalesce(ProductCard.processing_company_external_id, ""),
            func.coalesce(ProductCard.processing_company_title, ""),
            func.coalesce(ProductCard.processing_company_inn, ""),
            func.coalesce(ProductCard.processing_company_category, ""),
            func.coalesce(ProductCard.processing_company_origin, ""),
            ProductCard.status,
        )
        .all()
    )

    try:
        db.session.query(ProductCardCompanyStatsSnapshot).filter(
            ProductCardCompanyStatsSnapshot.snapshot_date == snapshot_date,
            ProductCardCompanyStatsSnapshot.snapshot_hour == snapshot_hour,
        ).delete(synchronize_session=False)

        snapshots = [
            ProductCardCompanyStatsSnapshot(
                snapshot_date=snapshot_date,
                snapshot_hour=snapshot_hour,
                snapshot_at=now,
                processing_company_external_id=row.external_id,
                processing_company_title=row.title,
                processing_company_inn=row.inn,
                processing_company_category=row.category,
                processing_company_origin=row.origin,
                status=row.status.value if hasattr(row.status, "value") else str(row.status or ""),
                cards_count=int(row.cards_count or 0),
            )
            for row in rows
        ]

        if snapshots:
            db.session.bulk_save_objects(snapshots)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to save product card company stats snapshot")
        raise

    return {
        "snapshot_date": snapshot_date.isoformat(),
        "snapshot_hour": snapshot_hour,
        "rows_saved": len(rows),
        "cards_count": sum(int(row.cards_count or 0) for row in rows),
    }
