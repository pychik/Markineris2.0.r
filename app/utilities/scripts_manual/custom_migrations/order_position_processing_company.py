"""Add processing company snapshot fields to order positions.

Usage from Flask shell:
    from utilities.scripts_manual.custom_migrations.order_position_processing_company import (
        preview_order_position_processing_company_migration,
        run_order_position_processing_company_migration,
    )

    preview_order_position_processing_company_migration()
    run_order_position_processing_company_migration()
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from models import db


TABLES = (
    "shoes",
    "linen",
    "parfum",
    "cosmetics",
    "toys",
    "clothes",
    "socks",
)

COLUMNS = (
    "processing_company_external_id",
    "processing_company_title",
    "processing_company_inn",
)


def preview_order_position_processing_company_migration() -> dict[str, Any]:
    rows = db.session.execute(text("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = ANY(:tables)
          AND column_name = ANY(:columns);
    """), {"tables": list(TABLES), "columns": list(COLUMNS)}).fetchall()
    existing = {(row.table_name, row.column_name) for row in rows}

    return {
        table: {
            column: (table, column) in existing
            for column in COLUMNS
        }
        for table in TABLES
    }


def run_order_position_processing_company_migration(*, commit: bool = True) -> dict[str, Any]:
    try:
        for table in TABLES:
            db.session.execute(text(f"""
                ALTER TABLE public.{table}
                ADD COLUMN IF NOT EXISTS processing_company_external_id VARCHAR(100),
                ADD COLUMN IF NOT EXISTS processing_company_title VARCHAR(255),
                ADD COLUMN IF NOT EXISTS processing_company_inn VARCHAR(20);
            """))
            db.session.execute(text(f"""
                UPDATE public.{table}
                SET processing_company_external_id = COALESCE(processing_company_external_id, ''),
                    processing_company_title = COALESCE(processing_company_title, ''),
                    processing_company_inn = COALESCE(processing_company_inn, '')
                WHERE processing_company_external_id IS NULL
                   OR processing_company_title IS NULL
                   OR processing_company_inn IS NULL;
            """))
            db.session.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{table}_processing_company_inn
                ON public.{table} (processing_company_inn);
            """))

        if commit:
            db.session.commit()
        else:
            db.session.flush()

        return preview_order_position_processing_company_migration()
    except Exception:
        db.session.rollback()
        raise
