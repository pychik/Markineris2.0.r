"""Add Tezaurus processing company fields to product cards.

Usage from Flask shell:
    from utilities.scripts_manual.custom_migrations.product_card_processing_company import (
        preview_product_card_processing_company_migration,
        run_product_card_processing_company_migration,
    )

    preview_product_card_processing_company_migration()
    run_product_card_processing_company_migration()
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from models import db


COLUMNS = (
    "processing_company_external_id",
    "processing_company_title",
    "processing_company_inn",
    "processing_company_origin",
    "processing_company_category",
    "processing_company_payload",
    "processing_company_assigned_at",
)


def _fetch_scalar(query: str):
    return db.session.execute(text(query)).scalar()


def preview_product_card_processing_company_migration() -> dict[str, Any]:
    """Return product card processing company migration state."""
    existing_columns = {
        row[0]
        for row in db.session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'product_cards'
              AND column_name = ANY(:columns);
        """), {"columns": list(COLUMNS)}).fetchall()
    }

    index_exists = bool(_fetch_scalar("""
        SELECT EXISTS (
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'product_cards'
              AND indexname = 'ix_product_cards_processing_company_inn'
        );
    """))

    return {
        "columns": {column: column in existing_columns for column in COLUMNS},
        "missing_columns": [column for column in COLUMNS if column not in existing_columns],
        "index_exists": index_exists,
    }


def run_product_card_processing_company_migration(*, commit: bool = True) -> dict[str, Any]:
    """Create nullable processing company fields and index company INN."""
    try:
        db.session.execute(text("""
            ALTER TABLE public.product_cards
            ADD COLUMN IF NOT EXISTS processing_company_external_id VARCHAR(100),
            ADD COLUMN IF NOT EXISTS processing_company_title VARCHAR(255),
            ADD COLUMN IF NOT EXISTS processing_company_inn VARCHAR(20),
            ADD COLUMN IF NOT EXISTS processing_company_origin VARCHAR(20),
            ADD COLUMN IF NOT EXISTS processing_company_category VARCHAR(50),
            ADD COLUMN IF NOT EXISTS processing_company_payload JSONB,
            ADD COLUMN IF NOT EXISTS processing_company_assigned_at TIMESTAMP WITHOUT TIME ZONE;
        """))

        db.session.execute(text("""
            UPDATE public.product_cards
            SET processing_company_external_id = COALESCE(processing_company_external_id, ''),
                processing_company_title = COALESCE(processing_company_title, ''),
                processing_company_inn = COALESCE(processing_company_inn, ''),
                processing_company_origin = COALESCE(processing_company_origin, ''),
                processing_company_category = COALESCE(processing_company_category, '')
            WHERE processing_company_external_id IS NULL
               OR processing_company_title IS NULL
               OR processing_company_inn IS NULL
               OR processing_company_origin IS NULL
               OR processing_company_category IS NULL;
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_product_cards_processing_company_inn
            ON public.product_cards (processing_company_inn);
        """))

        if commit:
            db.session.commit()
        else:
            db.session.flush()

        return preview_product_card_processing_company_migration()
    except Exception:
        db.session.rollback()
        raise
