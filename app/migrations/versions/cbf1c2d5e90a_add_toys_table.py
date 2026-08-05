"""add toys table

Revision ID: cbf1c2d5e90a
Revises: a10c0852418b
Create Date: 2026-08-04 17:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'cbf1c2d5e90a'
down_revision = 'a10c0852418b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'toys',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('type', sa.String(length=100), nullable=True),
        sa.Column('article_price', sa.Float(), nullable=True),
        sa.Column('tnved_code', sa.String(length=50), nullable=True),
        sa.Column('country', sa.String(length=58), nullable=True),
        sa.Column('tax', sa.Integer(), nullable=True),
        sa.Column('trademark', sa.String(length=100), nullable=True),
        sa.Column('rd_type', sa.String(length=50), nullable=True),
        sa.Column('rd_name', sa.String(length=100), nullable=True),
        sa.Column('rd_date', sa.Date(), nullable=True),
        sa.Column('rd_date_to', sa.Date(), nullable=True),
        sa.Column('subcategory', sa.String(length=64), nullable=False),
        sa.Column('full_name_extra', sa.String(length=255), nullable=True),
        sa.Column('category_code', sa.String(length=32), nullable=True),
        sa.Column('okpd2_code', sa.String(length=32), nullable=True),
        sa.Column('okpd2_name', sa.String(length=255), nullable=True),
        sa.Column('model_article_type', sa.String(length=32), nullable=True),
        sa.Column('model_article', sa.String(length=100), nullable=True),
        sa.Column('model_article_replace', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('material', sa.String(length=100), nullable=True),
        sa.Column('min_child_age', sa.String(length=32), nullable=True),
        sa.Column('usage_term_type', sa.String(length=100), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('service_life_type', sa.String(length=20), nullable=True),
        sa.Column('service_life', sa.Integer(), nullable=True),
        sa.Column('sl_date_from', sa.Date(), nullable=True),
        sa.Column('sl_date_to', sa.Date(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('card_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['card_id'], ['product_cards.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('toys', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_toys_card_id'), ['card_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_toys_order_id'), ['order_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_toys_rd_date_to'), ['rd_date_to'], unique=False)
        batch_op.create_index(batch_op.f('ix_toys_sl_date_to'), ['sl_date_to'], unique=False)
        batch_op.create_index(batch_op.f('ix_toys_subcategory'), ['subcategory'], unique=False)


def downgrade():
    with op.batch_alter_table('toys', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_toys_subcategory'))
        batch_op.drop_index(batch_op.f('ix_toys_sl_date_to'))
        batch_op.drop_index(batch_op.f('ix_toys_rd_date_to'))
        batch_op.drop_index(batch_op.f('ix_toys_order_id'))
        batch_op.drop_index(batch_op.f('ix_toys_card_id'))
    op.drop_table('toys')
