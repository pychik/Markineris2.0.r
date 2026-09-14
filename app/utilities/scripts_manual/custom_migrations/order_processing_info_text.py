"""Expand orders.processing_info to TEXT for multi-company UPD data.

Usage from Flask shell:
    from utilities.scripts_manual.custom_migrations.order_processing_info_text import (
        preview_order_processing_info_text_migration,
        run_order_processing_info_text_migration,
    )

    preview_order_processing_info_text_migration()
    run_order_processing_info_text_migration()
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from models import db


def preview_order_processing_info_text_migration() -> dict[str, Any]:
    row = db.session.execute(text("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'orders'
          AND column_name = 'processing_info';
    """)).first()

    return {"processing_info_type": row.data_type if row else None}


def run_order_processing_info_text_migration(*, commit: bool = True) -> dict[str, Any]:
    try:
        db.session.execute(text("""
            ALTER TABLE public.orders
            ALTER COLUMN processing_info TYPE TEXT;
        """))

        if commit:
            db.session.commit()
        else:
            db.session.flush()

        return preview_order_processing_info_text_migration()
    except Exception:
        db.session.rollback()
        raise
