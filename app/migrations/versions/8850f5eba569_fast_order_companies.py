"""add fast order companies

Revision ID: 8850f5eba569
Revises: c2a4f1d9b8e3
Create Date: 2026-09-27 10:00:37.158011

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = '8850f5eba569'
down_revision = 'c2a4f1d9b8e3'
branch_labels = None
depends_on = None


FAST_ORDER_POSITION_TABLES = (
    'clothes',
    'cosmetics',
    'linen',
    'parfum',
    'shoes',
    'socks',
    'toys',
)

PRODUCT_CARD_PROCESSING_COLUMNS = (
    ('processing_company_external_id', sa.Column('processing_company_external_id', sa.String(length=100), nullable=True)),
    ('processing_company_title', sa.Column('processing_company_title', sa.String(length=255), nullable=True)),
    ('processing_company_inn', sa.Column('processing_company_inn', sa.String(length=20), nullable=True)),
    ('processing_company_origin', sa.Column('processing_company_origin', sa.String(length=20), nullable=True)),
    ('processing_company_category', sa.Column('processing_company_category', sa.String(length=50), nullable=True)),
    ('processing_company_payload', sa.Column('processing_company_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True)),
    ('processing_company_assigned_at', sa.Column('processing_company_assigned_at', sa.DateTime(), nullable=True)),
)


def _inspector():
    return inspect(op.get_bind())


def _table_exists(table_name):
    return table_name in _inspector().get_table_names()


def _column_exists(table_name, column_name):
    if not _table_exists(table_name):
        return False
    return column_name in {column['name'] for column in _inspector().get_columns(table_name)}


def _index_exists(table_name, index_name):
    if not _table_exists(table_name):
        return False
    return index_name in {index['name'] for index in _inspector().get_indexes(table_name)}


def _fk_exists(table_name, column_name, referred_table):
    return _fk_name(table_name, column_name, referred_table) is not None


def _fk_name(table_name, column_name, referred_table):
    if not _table_exists(table_name):
        return None
    for fk in _inspector().get_foreign_keys(table_name):
        if fk.get('referred_table') == referred_table and column_name in fk.get('constrained_columns', []):
            return fk.get('name')
    return None


def _create_product_card_stats_table():
    if _table_exists('product_card_company_stats_snapshots'):
        return

    op.create_table(
        'product_card_company_stats_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('snapshot_hour', sa.Integer(), server_default='0', nullable=False),
        sa.Column('snapshot_at', sa.DateTime(), nullable=False),
        sa.Column('processing_company_external_id', sa.String(length=100), server_default='', nullable=False),
        sa.Column('processing_company_title', sa.String(length=255), server_default='', nullable=False),
        sa.Column('processing_company_inn', sa.String(length=20), server_default='', nullable=False),
        sa.Column('processing_company_category', sa.String(length=50), server_default='', nullable=False),
        sa.Column('processing_company_origin', sa.String(length=20), server_default='', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='', nullable=False),
        sa.Column('cards_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'snapshot_date',
            'snapshot_hour',
            'processing_company_inn',
            'processing_company_external_id',
            'processing_company_title',
            'processing_company_category',
            'processing_company_origin',
            'status',
            name='uq_pc_company_stats_snapshot_scope',
        ),
    )

    with op.batch_alter_table('product_card_company_stats_snapshots', schema=None) as batch_op:
        batch_op.create_index(
            'ix_pc_company_stats_snapshot_company_date',
            ['processing_company_inn', 'processing_company_external_id', 'snapshot_date', 'snapshot_hour'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_product_card_company_stats_snapshots_processing_company_category'),
            ['processing_company_category'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_product_card_company_stats_snapshots_processing_company_origin'),
            ['processing_company_origin'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_product_card_company_stats_snapshots_processing_company_inn'),
            ['processing_company_inn'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_product_card_company_stats_snapshots_snapshot_date'),
            ['snapshot_date'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_product_card_company_stats_snapshots_snapshot_hour'),
            ['snapshot_hour'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_product_card_company_stats_snapshots_status'),
            ['status'],
            unique=False,
        )


def _create_fast_order_companies_table():
    if _table_exists('fast_order_companies'):
        return

    op.create_table(
        'fast_order_companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('company_key', sa.String(length=255), nullable=False),
        sa.Column('processing_company_external_id', sa.String(length=100), server_default='', nullable=False),
        sa.Column('processing_company_title', sa.String(length=255), server_default='', nullable=False),
        sa.Column('processing_company_inn', sa.String(length=20), server_default='', nullable=False),
        sa.Column('upd_number', sa.String(length=100), server_default='', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name='fk_fast_order_companies_order_id_orders', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id', 'company_key', name='uq_fast_order_companies_order_company'),
    )

    with op.batch_alter_table('fast_order_companies', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_fast_order_companies_company_key'), ['company_key'], unique=False)
        batch_op.create_index(batch_op.f('ix_fast_order_companies_order_id'), ['order_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_fast_order_companies_processing_company_inn'), ['processing_company_inn'], unique=False)


def _add_fast_order_company_column(table_name):
    if not _table_exists(table_name):
        return

    index_name = f'ix_{table_name}_fast_order_company_id'
    fk_name = f'fk_{table_name}_fast_order_company_id_fast_order_companies'

    with op.batch_alter_table(table_name, schema=None) as batch_op:
        if not _column_exists(table_name, 'fast_order_company_id'):
            batch_op.add_column(sa.Column('fast_order_company_id', sa.Integer(), nullable=True))
        if not _index_exists(table_name, index_name):
            batch_op.create_index(batch_op.f(index_name), ['fast_order_company_id'], unique=False)
        if not _fk_exists(table_name, 'fast_order_company_id', 'fast_order_companies'):
            batch_op.create_foreign_key(
                fk_name,
                'fast_order_companies',
                ['fast_order_company_id'],
                ['id'],
                ondelete='SET NULL',
            )


def upgrade():
    _create_product_card_stats_table()
    _create_fast_order_companies_table()

    for table_name in FAST_ORDER_POSITION_TABLES:
        _add_fast_order_company_column(table_name)

    if _column_exists('orders', 'processing_info'):
        with op.batch_alter_table('orders', schema=None) as batch_op:
            batch_op.alter_column(
                'processing_info',
                existing_type=sa.VARCHAR(length=100),
                type_=sa.Text(),
                existing_nullable=True,
            )

    if _table_exists('product_cards'):
        existing_columns = {column['name'] for column in _inspector().get_columns('product_cards')}
        with op.batch_alter_table('product_cards', schema=None) as batch_op:
            for column_name, column in PRODUCT_CARD_PROCESSING_COLUMNS:
                if column_name not in existing_columns:
                    batch_op.add_column(column)


def downgrade():
    if _table_exists('product_cards'):
        existing_columns = {column['name'] for column in _inspector().get_columns('product_cards')}
        with op.batch_alter_table('product_cards', schema=None) as batch_op:
            for column_name, _column in reversed(PRODUCT_CARD_PROCESSING_COLUMNS):
                if column_name in existing_columns:
                    batch_op.drop_column(column_name)

    if _column_exists('orders', 'processing_info'):
        with op.batch_alter_table('orders', schema=None) as batch_op:
            batch_op.alter_column(
                'processing_info',
                existing_type=sa.Text(),
                type_=sa.VARCHAR(length=100),
                existing_nullable=True,
            )

    for table_name in reversed(FAST_ORDER_POSITION_TABLES):
        if not _table_exists(table_name) or not _column_exists(table_name, 'fast_order_company_id'):
            continue
        index_name = f'ix_{table_name}_fast_order_company_id'
        fk_name = f'fk_{table_name}_fast_order_company_id_fast_order_companies'
        existing_fk_name = _fk_name(table_name, 'fast_order_company_id', 'fast_order_companies')
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            if existing_fk_name:
                batch_op.drop_constraint(existing_fk_name or fk_name, type_='foreignkey')
            if _index_exists(table_name, index_name):
                batch_op.drop_index(batch_op.f(index_name))
            batch_op.drop_column('fast_order_company_id')

    if _table_exists('fast_order_companies'):
        op.drop_table('fast_order_companies')

    if _table_exists('product_card_company_stats_snapshots'):
        op.drop_table('product_card_company_stats_snapshots')
